"""
Batch Excel Import Manager

This module orchestrates the batch processing of multiple Excel files
and manages the complete import workflow.
"""

import os
import glob
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging
from tqdm import tqdm

from .excel_parser import ExcelChatRoomParser
from .data_transformer import ChatRoomDataTransformer
from .api_client import AnnotationAPIClient, APIError

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """Result of importing a single Excel file."""
    file_path: str
    base_name: str
    status: str  # 'success', 'error', 'skipped'
    chat_room_id: Optional[int] = None
    chat_room_name: Optional[str] = None
    users_created: List[str] = field(default_factory=list)
    total_messages: int = 0
    total_annotations: int = 0
    error_message: Optional[str] = None
    processing_time: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchImportResults:
    """Results of batch import operation."""
    total_files: int
    successful_imports: int
    failed_imports: int
    skipped_imports: int
    results: List[ImportResult] = field(default_factory=list)
    total_processing_time: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class BatchExcelImportManager:
    """
    Manages batch processing of Excel files for chat room import.
    
    Orchestrates the complete workflow from file discovery to API import.
    """
    
    def __init__(self, 
                 api_client: AnnotationAPIClient,
                 transformer: Optional[ChatRoomDataTransformer] = None,
                 project_id: int = 1,
                 skip_existing: bool = True):
        """
        Initialize the batch import manager.
        
        Args:
            api_client: API client for backend communication
            transformer: Data transformer (will create default if None)
            project_id: Project ID to import chat rooms into
            skip_existing: Whether to skip files that might already be imported
        """
        self.api_client = api_client
        self.transformer = transformer or ChatRoomDataTransformer()
        self.project_id = project_id
        self.skip_existing = skip_existing
        
        # Statistics tracking
        self.total_files_processed = 0
        self.total_chat_rooms_created = 0
        self.total_users_created = 0
        self.total_messages_imported = 0
        self.total_annotations_imported = 0
    
    def discover_excel_files(self, directory: str, pattern: str = "*.xlsx") -> List[str]:
        """
        Discover Excel files in a directory.
        
        Args:
            directory: Directory to search
            pattern: File pattern to match
            
        Returns:
            List of Excel file paths
        """
        directory_path = Path(directory)
        
        if not directory_path.exists():
            raise ValueError(f"Directory does not exist: {directory}")
        
        if not directory_path.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")
        
        # Find files matching pattern
        excel_files = []
        for file_path in directory_path.glob(pattern):
            if file_path.is_file():
                excel_files.append(str(file_path))
        
        # Also check for .xls files
        if pattern == "*.xlsx":
            for file_path in directory_path.glob("*.xls"):
                if file_path.is_file():
                    excel_files.append(str(file_path))
        
        logger.info(f"Discovered {len(excel_files)} Excel files in {directory}")
        return sorted(excel_files)
    
    def should_skip_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Determine if a file should be skipped.
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            Tuple of (should_skip, reason)
        """
        if not self.skip_existing:
            return False, ""
        
        # Extract base name from file
        base_name = Path(file_path).stem
        
        # Check if a chat room with similar name already exists
        # This is a simplified check - in production you might want more sophisticated logic
        try:
            projects = self.api_client.get_projects()
            for project in projects:
                if project['id'] == self.project_id:
                    # You could implement a more sophisticated check here
                    # For now, we'll be conservative and not skip
                    break
        except APIError:
            pass  # If we can't check, don't skip
        
        return False, ""
    
    def process_single_file(self, file_path: str, show_progress: bool = True) -> ImportResult:
        """
        Process a single Excel file.
        
        Args:
            file_path: Path to the Excel file
            show_progress: Whether to show progress bars
            
        Returns:
            ImportResult object
        """
        start_time = datetime.now()
        file_path = str(Path(file_path).resolve())
        base_name = Path(file_path).stem
        
        result = ImportResult(
            file_path=file_path,
            base_name=base_name,
            status="processing"
        )
        
        try:
            # Check if file should be skipped
            should_skip, skip_reason = self.should_skip_file(file_path)
            if should_skip:
                result.status = "skipped"
                result.error_message = skip_reason
                return result
            
            logger.info(f"Processing file: {file_path}")
            
            # Step 1: Parse Excel file
            if show_progress:
                print(f"📖 Parsing Excel file: {Path(file_path).name}")
            
            parser = ExcelChatRoomParser(file_path)
            sheets_data = parser.get_all_sheets_data()
            
            if not sheets_data:
                result.status = "error"
                result.error_message = "No valid sheets found in Excel file"
                return result
            
            # Step 2: Validate consistency
            is_consistent, consistency_errors = parser.validate_consistency()
            if not is_consistent:
                result.status = "error"
                result.error_message = f"Inconsistent data: {'; '.join(consistency_errors)}"
                return result
            
            # Step 3: Transform data
            if show_progress:
                print(f"🔄 Transforming data for API import")
            
            # Always use the API client's current project ID if available
            # This ensures we use the correct project even if it was created dynamically
            if hasattr(self.api_client, 'current_project_id') and self.api_client.current_project_id:
                actual_project_id = self.api_client.current_project_id
                logger.info(f"Using API client's current project ID: {actual_project_id}")
            else:
                actual_project_id = self.project_id
                logger.info(f"Using configured project ID: {actual_project_id}")
            
            import_data = self.transformer.prepare_chat_room_import_data(sheets_data, actual_project_id)
            
            # Step 4: Validate import data
            validation_errors = self.transformer.validate_import_data(import_data)
            if validation_errors:
                result.status = "error"
                result.error_message = f"Data validation failed: {'; '.join(validation_errors)}"
                return result
            
            # Step 5: Create users
            if show_progress:
                print(f"👥 Creating {len(import_data['users'])} users")
            
            users_data = [self.transformer.convert_to_api_format(user) for user in import_data['users']]
            user_username_to_id = self.api_client.batch_create_users(users_data)
            
            if not user_username_to_id:
                result.status = "error"
                result.error_message = "Failed to create any users"
                return result
            
            result.users_created = list(user_username_to_id.keys())
            
            # Step 6: Assign users to project
            if show_progress:
                print(f"🔗 Assigning users to project {actual_project_id}")
            
            user_ids = list(user_username_to_id.values())
            assigned_users = self.api_client.batch_assign_users_to_project(actual_project_id, user_ids)
            
            # Step 7: Create chat room and import messages in one operation
            if show_progress:
                print(f"🏠 Creating chat room and importing {len(import_data['messages'])} messages")
            
            chat_room_data = self.transformer.convert_to_api_format(import_data['chat_room'])
            messages_csv = self.transformer.prepare_csv_import_data(import_data['messages'])
            
            combined_result = self.api_client.create_chat_room_and_import_messages(
                project_id=actual_project_id,
                name=chat_room_data['name'],
                messages_csv=messages_csv
            )
            
            result.chat_room_id = combined_result['chat_room']['id']
            result.chat_room_name = combined_result['chat_room']['name']
            result.total_messages = combined_result['import_details']['imported_count']
            
            # Step 8: Import annotations for each user
            total_annotations = 0
            annotations_by_user = import_data['annotations_by_user']
            
            if show_progress:
                print(f"📝 Importing annotations for {len(annotations_by_user)} users")
                pbar = tqdm(annotations_by_user.items(), desc="Importing annotations")
            else:
                pbar = annotations_by_user.items()
            
            for username, annotations in pbar:
                if username not in user_username_to_id:
                    logger.warning(f"User {username} not found in created users")
                    continue
                
                user_id = user_username_to_id[username]
                
                if annotations:  # Only import if there are annotations
                    annotations_csv = self.transformer.prepare_annotations_import_data(annotations)
                    annotations_result = self.api_client.import_annotations(
                        result.chat_room_id, user_id, annotations_csv
                    )
                    total_annotations += annotations_result.get('imported_count', 0)
            
            result.total_annotations = total_annotations
            
            # Step 9: Finalize result
            result.status = "success"
            result.details = {
                "sheets_processed": len(sheets_data),
                "annotators": import_data['annotators'],
                "users_assigned": len(assigned_users),
                "import_summary": self.transformer.generate_import_summary(import_data)
            }
            
            logger.info(f"Successfully processed {file_path}: "
                       f"Chat room {result.chat_room_id}, "
                       f"{result.total_messages} messages, "
                       f"{result.total_annotations} annotations")
            
        except Exception as e:
            result.status = "error"
            result.error_message = str(e)
            logger.error(f"Failed to process {file_path}: {e}")
        
        finally:
            # Calculate processing time
            end_time = datetime.now()
            result.processing_time = (end_time - start_time).total_seconds()
        
        return result
    
    def process_directory(self, 
                         directory: str,
                         pattern: str = "*.xlsx",
                         show_progress: bool = True) -> BatchImportResults:
        """
        Process all Excel files in a directory.
        
        Args:
            directory: Directory containing Excel files
            pattern: File pattern to match
            show_progress: Whether to show progress information
            
        Returns:
            BatchImportResults object
        """
        start_time = datetime.now()
        
        # Discover files
        excel_files = self.discover_excel_files(directory, pattern)
        
        if not excel_files:
            logger.warning(f"No Excel files found in {directory}")
            return BatchImportResults(
                total_files=0,
                successful_imports=0,
                failed_imports=0,
                skipped_imports=0,
                start_time=start_time,
                end_time=datetime.now()
            )
        
        # Initialize results
        batch_results = BatchImportResults(
            total_files=len(excel_files),
            successful_imports=0,
            failed_imports=0,
            skipped_imports=0,
            start_time=start_time
        )
        
        # Process files
        if show_progress:
            print(f"🚀 Starting batch import of {len(excel_files)} Excel files")
            files_pbar = tqdm(excel_files, desc="Processing files")
        else:
            files_pbar = excel_files
        
        for file_path in files_pbar:
            if show_progress:
                files_pbar.set_description(f"Processing {Path(file_path).name}")
            
            result = self.process_single_file(file_path, show_progress=False)
            batch_results.results.append(result)
            
            # Update counters
            if result.status == "success":
                batch_results.successful_imports += 1
                self.total_chat_rooms_created += 1
                self.total_users_created += len(result.users_created)
                self.total_messages_imported += result.total_messages
                self.total_annotations_imported += result.total_annotations
            elif result.status == "error":
                batch_results.failed_imports += 1
            elif result.status == "skipped":
                batch_results.skipped_imports += 1
            
            self.total_files_processed += 1
        
        # Finalize results
        batch_results.end_time = datetime.now()
        batch_results.total_processing_time = (batch_results.end_time - batch_results.start_time).total_seconds()
        
        if show_progress:
            self.print_batch_summary(batch_results)
        
        return batch_results
    
    def process_file_list(self, 
                         file_paths: List[str],
                         show_progress: bool = True) -> BatchImportResults:
        """
        Process a specific list of Excel files.
        
        Args:
            file_paths: List of Excel file paths
            show_progress: Whether to show progress information
            
        Returns:
            BatchImportResults object
        """
        start_time = datetime.now()
        
        # Validate files exist
        valid_files = []
        for file_path in file_paths:
            if Path(file_path).exists():
                valid_files.append(file_path)
            else:
                logger.warning(f"File not found: {file_path}")
        
        if not valid_files:
            logger.warning("No valid files to process")
            return BatchImportResults(
                total_files=0,
                successful_imports=0,
                failed_imports=0,
                skipped_imports=0,
                start_time=start_time,
                end_time=datetime.now()
            )
        
        # Initialize results
        batch_results = BatchImportResults(
            total_files=len(valid_files),
            successful_imports=0,
            failed_imports=0,
            skipped_imports=0,
            start_time=start_time
        )
        
        # Process files
        if show_progress:
            print(f"🚀 Starting batch import of {len(valid_files)} Excel files")
            files_pbar = tqdm(valid_files, desc="Processing files")
        else:
            files_pbar = valid_files
        
        for file_path in files_pbar:
            if show_progress:
                files_pbar.set_description(f"Processing {Path(file_path).name}")
            
            result = self.process_single_file(file_path, show_progress=False)
            batch_results.results.append(result)
            
            # Update counters
            if result.status == "success":
                batch_results.successful_imports += 1
                self.total_chat_rooms_created += 1
                self.total_users_created += len(result.users_created)
                self.total_messages_imported += result.total_messages
                self.total_annotations_imported += result.total_annotations
            elif result.status == "error":
                batch_results.failed_imports += 1
            elif result.status == "skipped":
                batch_results.skipped_imports += 1
            
            self.total_files_processed += 1
        
        # Finalize results
        batch_results.end_time = datetime.now()
        batch_results.total_processing_time = (batch_results.end_time - batch_results.start_time).total_seconds()
        
        if show_progress:
            self.print_batch_summary(batch_results)
        
        return batch_results
    
    def print_batch_summary(self, results: BatchImportResults):
        """Print a summary of batch import results."""
        print("\n" + "="*70)
        print("🎉 BATCH IMPORT SUMMARY")
        print("="*70)
        print(f"📊 Total files processed: {results.total_files}")
        print(f"✅ Successful imports: {results.successful_imports}")
        print(f"❌ Failed imports: {results.failed_imports}")
        print(f"⏭️  Skipped imports: {results.skipped_imports}")
        print(f"⏱️  Total processing time: {results.total_processing_time:.2f} seconds")
        print(f"🏠 Chat rooms created: {self.total_chat_rooms_created}")
        print(f"👥 Users created: {self.total_users_created}")
        print(f"💬 Messages imported: {self.total_messages_imported}")
        print(f"📝 Annotations imported: {self.total_annotations_imported}")
        
        if results.failed_imports > 0:
            print("\n❌ FAILED IMPORTS:")
            for result in results.results:
                if result.status == "error":
                    print(f"  • {Path(result.file_path).name}: {result.error_message}")
        
        if results.skipped_imports > 0:
            print("\n⏭️  SKIPPED IMPORTS:")
            for result in results.results:
                if result.status == "skipped":
                    print(f"  • {Path(result.file_path).name}: {result.error_message}")
        
        print("="*70)
    
    def generate_detailed_report(self, results: BatchImportResults) -> str:
        """
        Generate a detailed report of the batch import.
        
        Args:
            results: Batch import results
            
        Returns:
            Detailed report as string
        """
        report = []
        report.append("DETAILED BATCH IMPORT REPORT")
        report.append("="*50)
        report.append(f"Start time: {results.start_time}")
        report.append(f"End time: {results.end_time}")
        report.append(f"Total processing time: {results.total_processing_time:.2f} seconds")
        report.append(f"Project ID: {self.project_id}")
        report.append("")
        
        # Summary statistics
        report.append("SUMMARY STATISTICS")
        report.append("-"*20)
        report.append(f"Total files: {results.total_files}")
        report.append(f"Successful: {results.successful_imports}")
        report.append(f"Failed: {results.failed_imports}")
        report.append(f"Skipped: {results.skipped_imports}")
        report.append(f"Success rate: {results.successful_imports/results.total_files*100:.1f}%")
        report.append("")
        
        # Detailed results
        report.append("DETAILED RESULTS")
        report.append("-"*20)
        for result in results.results:
            report.append(f"File: {Path(result.file_path).name}")
            report.append(f"  Status: {result.status}")
            report.append(f"  Processing time: {result.processing_time:.2f}s")
            
            if result.status == "success":
                report.append(f"  Chat room: {result.chat_room_name} (ID: {result.chat_room_id})")
                report.append(f"  Users created: {len(result.users_created)}")
                report.append(f"  Messages imported: {result.total_messages}")
                report.append(f"  Annotations imported: {result.total_annotations}")
                if result.details:
                    report.append(f"  Annotators: {', '.join(result.details.get('annotators', []))}")
            elif result.status == "error":
                report.append(f"  Error: {result.error_message}")
            elif result.status == "skipped":
                report.append(f"  Reason: {result.error_message}")
            
            report.append("")
        
        return "\n".join(report)
    
    def save_report(self, results: BatchImportResults, output_path: str):
        """
        Save detailed report to file.
        
        Args:
            results: Batch import results
            output_path: Path to save report
        """
        report = self.generate_detailed_report(results)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"Detailed report saved to: {output_path}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get current statistics."""
        return {
            "total_files_processed": self.total_files_processed,
            "total_chat_rooms_created": self.total_chat_rooms_created,
            "total_users_created": self.total_users_created,
            "total_messages_imported": self.total_messages_imported,
            "total_annotations_imported": self.total_annotations_imported,
            "project_id": self.project_id
        } 
