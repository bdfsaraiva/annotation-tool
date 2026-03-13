import React from 'react';
import './IAAMatrix.css';

const IAAMatrix = ({ pairwiseAccuracies, annotators }) => {
    // Create a lookup map for quick access to accuracy scores
    const accuracyMap = new Map();
    pairwiseAccuracies.forEach(pair => {
        const key1 = `${pair.annotator_1_id}-${pair.annotator_2_id}`;
        const key2 = `${pair.annotator_2_id}-${pair.annotator_1_id}`;
        accuracyMap.set(key1, pair.accuracy);
        accuracyMap.set(key2, pair.accuracy);
    });

    // Helper function to get accuracy between two annotators
    const getAccuracy = (annotatorId1, annotatorId2) => {
        if (annotatorId1 === annotatorId2) return 100; // Perfect agreement with self
        const key = `${annotatorId1}-${annotatorId2}`;
        return accuracyMap.get(key) || null;
    };

    // Helper function to get color based on accuracy score
    const getColor = (accuracy) => {
        if (accuracy === null) return '#f8f9fa'; // Light gray for no data
        if (accuracy === 100) return '#e8f5e8'; // Light green for self-comparison
        
        // Color scale from red (low agreement) to green (high agreement)
        const hue = (accuracy / 100) * 120; // 0 = red, 120 = green
        const saturation = 70;
        const lightness = 85;
        return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
    };

    // Helper function to get text color for readability
    const getTextColor = (accuracy) => {
        if (accuracy === null) return '#6c757d';
        if (accuracy === 100) return '#28a745';
        return accuracy > 50 ? '#155724' : '#721c24';
    };

    return (
        <div className="iaa-matrix">
            <table className="matrix-table">
                <thead>
                    <tr>
                        <th className="matrix-header-empty"></th>
                        {annotators.map(annotator => (
                            <th key={annotator.id} className="matrix-header">
                                <div className="annotator-header">
                                    <span className="annotator-name">{annotator.username}</span>
                                </div>
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {annotators.map(rowAnnotator => (
                        <tr key={rowAnnotator.id}>
                            <td className="matrix-row-header">
                                <div className="annotator-header">
                                    <span className="annotator-name">{rowAnnotator.username}</span>
                                </div>
                            </td>
                            {annotators.map(colAnnotator => {
                                const accuracy = getAccuracy(rowAnnotator.id, colAnnotator.id);
                                const isUpperTriangle = annotators.findIndex(a => a.id === rowAnnotator.id) < 
                                                       annotators.findIndex(a => a.id === colAnnotator.id);
                                const isSelf = rowAnnotator.id === colAnnotator.id;
                                
                                return (
                                    <td 
                                        key={colAnnotator.id} 
                                        className={`matrix-cell ${isSelf ? 'self-cell' : ''} ${isUpperTriangle ? 'upper-triangle' : ''}`}
                                        style={{ 
                                            backgroundColor: getColor(accuracy),
                                            color: getTextColor(accuracy)
                                        }}
                                        title={
                                            isSelf 
                                                ? `${rowAnnotator.username} (self)`
                                                : accuracy !== null 
                                                    ? `${rowAnnotator.username} vs ${colAnnotator.username}: ${accuracy.toFixed(1)}%`
                                                    : 'No data available'
                                        }
                                    >
                                        {isSelf ? (
                                            <span className="self-indicator">—</span>
                                        ) : accuracy !== null ? (
                                            <span className="accuracy-value">{accuracy.toFixed(1)}%</span>
                                        ) : (
                                            <span className="no-data">—</span>
                                        )}
                                    </td>
                                );
                            })}
                        </tr>
                    ))}
                </tbody>
            </table>
            
            <div className="matrix-legend">
                <h4>Legend</h4>
                <div className="legend-items">
                    <div className="legend-item">
                        <div className="legend-color" style={{ backgroundColor: '#f8d7da' }}></div>
                        <span>Low Agreement (0-50%)</span>
                    </div>
                    <div className="legend-item">
                        <div className="legend-color" style={{ backgroundColor: '#fff3cd' }}></div>
                        <span>Medium Agreement (50-75%)</span>
                    </div>
                    <div className="legend-item">
                        <div className="legend-color" style={{ backgroundColor: '#d4edda' }}></div>
                        <span>High Agreement (75-100%)</span>
                    </div>
                    <div className="legend-item">
                        <div className="legend-color" style={{ backgroundColor: '#e8f5e8' }}></div>
                        <span>Self-comparison</span>
                    </div>
                </div>
                <p className="legend-note">
                    <strong>Note:</strong> The matrix shows agreement scores between each pair of annotators. 
                    Higher percentages indicate better agreement on thread assignments.
                </p>
            </div>
        </div>
    );
};

export default IAAMatrix; 
