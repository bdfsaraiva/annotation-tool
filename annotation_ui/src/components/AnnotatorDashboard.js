import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { projects } from '../utils/api';
import { useAuth } from '../contexts/AuthContext';
import LoadingSpinner from './LoadingSpinner';
import ErrorMessage from './ErrorMessage';
import './AnnotatorDashboard.css';

const AnnotatorDashboard = () => {
    const [projectsList, setProjectsList] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const { currentUser } = useAuth();

    useEffect(() => {
        const fetchProjects = async () => {
            try {
                // The backend automatically returns only projects assigned to the current user.
                const response = await projects.listProjects();
                setProjectsList(response.projects);
            } catch (err) {
                setError(err.response?.data?.detail || err.message || 'Failed to fetch projects');
            } finally {
                setLoading(false);
            }
        };

        fetchProjects();
    }, []);

    if (loading) {
        return <LoadingSpinner message="Loading your projects..." size="large" />;
    }

    if (error) {
        return (
            <ErrorMessage 
                message={error} 
                title="Dashboard Error"
                onRetry={() => window.location.reload()}
            />
        );
    }

    return (
        <div className="annotator-dashboard">
            <div className="dashboard-header">
                <h2>Annotator Dashboard</h2>
                <p>Welcome, {currentUser?.username}! Here are your assigned projects.</p>
                {projectsList.length > 0 && (
                    <div className="dashboard-stats">
                        <span className="stat-item">
                            {projectsList.length} Project{projectsList.length !== 1 ? 's' : ''} Assigned
                        </span>
                    </div>
                )}
            </div>

            <div className="projects-grid">
                {projectsList.length === 0 ? (
                    <div className="empty-state">
                        <p>You haven't been assigned to any projects yet.</p>
                        <p>Contact your administrator to get started with annotation tasks.</p>
                    </div>
                ) : (
                    projectsList.map(project => (
                        <Link 
                            key={project.id} 
                            to={`/projects/${project.id}`} 
                            className="project-card-link"
                        >
                            <div className="project-card">
                                <div className="project-header">
                                    <h3>{project.name}</h3>
                                    <p className="project-description">{project.description || 'No description available'}</p>
                                </div>
                                <div className="project-meta">
                                    <span className="project-date">
                                        Created: {new Date(project.created_at).toLocaleDateString()}
                                    </span>
                                </div>
                                <div className="project-footer">
                                    <span>Start Annotating →</span>
                                </div>
                            </div>
                        </Link>
                    ))
                )}
            </div>
        </div>
    );
};

export default AnnotatorDashboard; 
