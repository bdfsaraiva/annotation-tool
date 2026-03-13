import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { annotations as annotationsApi, projects as projectsApi } from '../utils/api';
import IAAMatrix from './IAAMatrix';
import './AnnotationAnalysisPage.css';

const AnnotationAnalysisPage = () => {
    const { projectId, roomId } = useParams();
    const navigate = useNavigate();
    
    const [project, setProject] = useState(null);
    const [chatRoom, setChatRoom] = useState(null);
    const [iaaData, setIaaData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            setError(null);
            
            try {
                // Fetch project, chat room, and IAA data in parallel
                const [projectData, chatRoomData, iaaAnalysis] = await Promise.all([
                    projectsApi.getProject(projectId),
                    projectsApi.getChatRoom(projectId, roomId),
                    annotationsApi.getChatRoomIAA(roomId)
                ]);
                
                setProject(projectData);
                setChatRoom(chatRoomData);
                setIaaData(iaaAnalysis);
            } catch (err) {
                console.error('Failed to fetch analysis data:', err);
                setError(err.response?.data?.detail || 'Failed to load analysis data');
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [projectId, roomId]);

    const getStatusInfo = (status) => {
        const statusMap = {
            'Complete': {
                class: 'status-complete',
                title: 'Analysis Complete',
                description: 'All assigned annotators have completed their work'
            },
            'Partial': {
                class: 'status-partial',
                title: 'Partial Analysis',
                description: 'Some annotators have completed their work, analysis based on completed subset'
            },
            'NotEnoughData': {
                class: 'status-insufficient',
                title: 'Insufficient Data',
                description: 'Not enough completed annotations for analysis (need at least 2 annotators)'
            },
            'Error': {
                class: 'status-error',
                title: 'Analysis Error',
                description: 'An error occurred while calculating the analysis'
            }
        };
        
        return statusMap[status] || {
            class: 'status-unknown',
            title: 'Unknown Status',
            description: 'Unable to determine analysis status'
        };
    };

    const calculateAverageAgreement = () => {
        if (!iaaData?.pairwise_accuracies || iaaData.pairwise_accuracies.length === 0) {
            return null;
        }
        
        const sum = iaaData.pairwise_accuracies.reduce((acc, pair) => acc + pair.accuracy, 0);
        return (sum / iaaData.pairwise_accuracies.length).toFixed(1);
    };

    if (loading) {
        return <div className="loading-container">Loading analysis...</div>;
    }

    if (error) {
        return (
            <div className="error-container">
                <h2>Error Loading Analysis</h2>
                <p>{error}</p>
                <button onClick={() => navigate(`/admin/projects/${projectId}`)} className="action-button">
                    ← Back to Project
                </button>
            </div>
        );
    }

    if (!iaaData) {
        return <div>No analysis data available.</div>;
    }

    const statusInfo = getStatusInfo(iaaData.analysis_status);
    const averageAgreement = calculateAverageAgreement();

    return (
        <div className="annotation-analysis-page">
            <header className="page-header">
                <button 
                    onClick={() => navigate(`/admin/projects/${projectId}`)} 
                    className="back-button"
                >
                    ← Back to Project
                </button>
                <div className="header-content">
                    <h1>Inter-Annotator Agreement Analysis</h1>
                    <div className="breadcrumb">
                        <span>{project?.name}</span> → <span>{chatRoom?.name || iaaData.chat_room_name}</span>
                    </div>
                </div>
            </header>

            {/* Status Banner */}
            <div className={`status-banner ${statusInfo.class}`}>
                <div className="status-content">
                    <h2>{statusInfo.title}</h2>
                    <p>{statusInfo.description}</p>
                    {iaaData.analysis_status === 'Partial' && (
                        <div className="annotator-status">
                            <div className="annotator-group">
                                <strong>Completed ({iaaData.completed_annotators.length}):</strong>
                                <ul>
                                    {iaaData.completed_annotators.map(annotator => (
                                        <li key={annotator.id}>{annotator.username}</li>
                                    ))}
                                </ul>
                            </div>
                            <div className="annotator-group">
                                <strong>Pending ({iaaData.pending_annotators.length}):</strong>
                                <ul>
                                    {iaaData.pending_annotators.map(annotator => (
                                        <li key={annotator.id}>{annotator.username}</li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Statistics Section */}
            <div className="statistics-section">
                <h2>Chat Room Statistics</h2>
                <div className="stats-grid">
                    <div className="stat-card">
                        <h3>Chat Room</h3>
                        <p>{iaaData.chat_room_name}</p>
                    </div>
                    <div className="stat-card">
                        <h3>Total Turns</h3>
                        <p>{iaaData.message_count}</p>
                    </div>
                    <div className="stat-card">
                        <h3>Annotators</h3>
                        <p>{iaaData.completed_annotators.length} / {iaaData.total_annotators_assigned}</p>
                    </div>
                    <div className="stat-card">
                        <h3>Average Agreement</h3>
                        <p>{averageAgreement ? `${averageAgreement}%` : 'N/A'}</p>
                    </div>
                </div>
            </div>

            {/* IAA Matrix Section */}
            {iaaData.pairwise_accuracies.length > 0 && (
                <div className="matrix-section">
                    <h2>One-to-One Agreement Matrix</h2>
                    <p className="matrix-description">
                        This matrix shows the pairwise agreement scores between annotators. 
                        Higher percentages indicate better agreement between annotators.
                    </p>
                    <IAAMatrix 
                        pairwiseAccuracies={iaaData.pairwise_accuracies}
                        annotators={iaaData.completed_annotators}
                    />
                </div>
            )}

            {/* No Analysis Available */}
            {iaaData.pairwise_accuracies.length === 0 && (
                <div className="no-analysis">
                    <h2>No Analysis Available</h2>
                    <p>
                        Inter-annotator agreement analysis requires at least 2 annotators to have 
                        completed annotating all turns in this chat room.
                    </p>
                    <div className="current-status">
                        <p><strong>Current Status:</strong></p>
                        <p>• {iaaData.completed_annotators.length} annotator(s) completed</p>
                        <p>• {iaaData.pending_annotators.length} annotator(s) pending</p>
                        <p>• {iaaData.message_count} total turns to annotate</p>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AnnotationAnalysisPage; 
