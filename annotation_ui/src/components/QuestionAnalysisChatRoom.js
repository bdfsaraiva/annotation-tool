/**
 * @fileoverview Annotator interface for the ``question_analysis`` project type.
 *
 * Renders each chat turn with a compact annotation panel: a free-form ``label``
 * input plus three checkboxes (``trigger_marker``, ``borderline``, ``multiform``).
 * One persisted row per (message, annotator) pair; the backend upserts on POST.
 *
 * The component owns its own data fetch and is intended to be rendered as an
 * early branch inside ``AnnotatorChatRoomPage`` when ``project.annotation_type``
 * equals ``"question_analysis"``.
 */
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    projects as projectsApi,
    questionAnalysis as qaApi,
    auth,
} from '../utils/api';
import Modal from './Modal';
import ErrorMessage from './ErrorMessage';
import './QuestionAnalysisChatRoom.css';

const parseApiError = (error) => {
    if (error.response?.data?.detail) return error.response.data.detail;
    return error.message || 'An unexpected error occurred';
};

/** Short summary of the trigger-marker rubric shown in the help popover. */
const TRIGGER_RUBRIC = [
    'Primary check: the turn carries a question mark.',
    'Bare interrogative fragment (e.g. "Porquê", "Como assim").',
    'Turn-initial wh-word in matrix interrogative use (não relativo nem encaixado).',
    'Dedicated interrogative construction (será que…, não será (que)…).',
    'Disjunctive choice question (e.g. "Universal ou diversa").',
    'Conventionalised answer-soliciting formula (e.g. "alguém sabe…", "o que acham").',
];

const QuestionAnalysisChatRoom = () => {
    const { projectId, roomId } = useParams();
    const navigate = useNavigate();

    const [messages, setMessages] = useState([]);
    const [annotationsByMessage, setAnnotationsByMessage] = useState({});
    const [currentUser, setCurrentUser] = useState(null);
    const [chatRoomName, setChatRoomName] = useState('');
    const [project, setProject] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [savingMessageId, setSavingMessageId] = useState(null);
    const [showRubric, setShowRubric] = useState(false);
    const [isCompleted, setIsCompleted] = useState(false);
    const [isCompletionSaving, setIsCompletionSaving] = useState(false);

    // Local draft state per message — keeps the UI responsive between saves.
    const [drafts, setDrafts] = useState({});

    const fetchData = useCallback(async () => {
        if (!projectId || !roomId) return;
        setLoading(true);
        setError(null);
        try {
            const [projectData, roomData, messagesResponse, userData, qaRows, completionData] = await Promise.all([
                projectsApi.getProject(projectId),
                projectsApi.getChatRoom(projectId, roomId),
                projectsApi.getChatMessages(projectId, roomId),
                auth.getCurrentUser(),
                qaApi.getChatRoomAnnotations(projectId, roomId),
                projectsApi.getChatRoomCompletion(projectId, roomId),
            ]);
            setProject(projectData);
            setChatRoomName(roomData?.name || '');
            setMessages(messagesResponse.messages || []);
            setCurrentUser(userData);
            setIsCompleted(Boolean(completionData?.is_completed));

            const byMessage = {};
            const initialDrafts = {};
            (qaRows || []).forEach(row => {
                if (row.annotator_id === userData.id) {
                    byMessage[row.message_id] = row;
                    initialDrafts[row.message_id] = {
                        label: row.label || '',
                        trigger_marker: !!row.trigger_marker,
                        borderline: !!row.borderline,
                        multiform: !!row.multiform,
                    };
                }
            });
            setAnnotationsByMessage(byMessage);
            setDrafts(initialDrafts);
        } catch (err) {
            console.error('Question-analysis fetch error:', err);
            setError(parseApiError(err));
        } finally {
            setLoading(false);
        }
    }, [projectId, roomId]);

    useEffect(() => { fetchData(); }, [fetchData]);

    /** Update the local draft for a single message without persisting yet. */
    const updateDraft = (messageId, patch) => {
        setDrafts(prev => ({
            ...prev,
            [messageId]: {
                label: '',
                trigger_marker: false,
                borderline: false,
                multiform: false,
                ...(prev[messageId] || {}),
                ...patch,
            },
        }));
    };

    /** Persist the current draft for a single message (upsert). */
    const saveAnnotation = async (messageId) => {
        const draft = drafts[messageId];
        if (!draft || !draft.label?.trim()) {
            setError('A label is required before saving.');
            return;
        }
        setSavingMessageId(messageId);
        try {
            const payload = {
                message_id: messageId,
                label: draft.label.trim(),
                trigger_marker: !!draft.trigger_marker,
                borderline: !!draft.borderline,
                multiform: !!draft.multiform,
            };
            const saved = await qaApi.upsertAnnotation(projectId, roomId, payload);
            setAnnotationsByMessage(prev => ({ ...prev, [messageId]: saved }));
        } catch (err) {
            console.error('Save error:', err);
            setError(parseApiError(err));
        } finally {
            setSavingMessageId(null);
        }
    };

    const annotatedCount = useMemo(
        () => Object.keys(annotationsByMessage).length,
        [annotationsByMessage]
    );
    const totalCount = messages.length;
    const percent = totalCount === 0 ? 0 : Math.round((annotatedCount / totalCount) * 100);

    const toggleCompletion = async () => {
        const nextValue = !isCompleted;
        setIsCompletionSaving(true);
        try {
            await projectsApi.updateChatRoomCompletion(projectId, roomId, nextValue);
            setIsCompleted(nextValue);
        } catch (err) {
            setError(parseApiError(err));
        } finally {
            setIsCompletionSaving(false);
        }
    };

    if (loading) {
        return <div className="qa-loading">Loading…</div>;
    }

    return (
        <div className="qa-chat-room">
            <header className="qa-header">
                <button className="qa-back" onClick={() => navigate(`/projects/${projectId}`)}>
                    ← Back
                </button>
                <div className="qa-title">
                    <h2>{chatRoomName || 'Question Analysis'}</h2>
                    <div className="qa-progress">
                        {annotatedCount}/{totalCount} annotated ({percent}%)
                    </div>
                </div>
                <div className="qa-header-actions">
                    <button
                        type="button"
                        className="qa-help-btn"
                        onClick={() => setShowRubric(true)}
                    >
                        Rubric
                    </button>
                    <label className="qa-completion-toggle">
                        <input
                            type="checkbox"
                            checked={isCompleted}
                            disabled={isCompletionSaving}
                            onChange={toggleCompletion}
                        />
                        Mark room as completed
                    </label>
                </div>
            </header>

            {error && (
                <Modal isOpen={!!error} onClose={() => setError(null)}>
                    <ErrorMessage message={error} onDismiss={() => setError(null)} />
                </Modal>
            )}

            {showRubric && (
                <Modal isOpen={showRubric} onClose={() => setShowRubric(false)}>
                    <div className="qa-rubric">
                        <h3>Trigger marker rubric</h3>
                        <p>
                            A turn is question-form when its surface wording is unambiguously
                            interrogative. Mark only forms that cannot reasonably be read as
                            non-questions.
                        </p>
                        <ol>
                            {TRIGGER_RUBRIC.map((line, idx) => (
                                <li key={idx}>{line}</li>
                            ))}
                        </ol>
                        <button onClick={() => setShowRubric(false)}>Close</button>
                    </div>
                </Modal>
            )}

            <main className="qa-messages">
                {messages.map((msg) => {
                    const draft = drafts[msg.id] || {
                        label: '',
                        trigger_marker: false,
                        borderline: false,
                        multiform: false,
                    };
                    const saved = annotationsByMessage[msg.id];
                    const dirty = !saved
                        || saved.label !== draft.label
                        || !!saved.trigger_marker !== !!draft.trigger_marker
                        || !!saved.borderline !== !!draft.borderline
                        || !!saved.multiform !== !!draft.multiform;

                    return (
                        <article key={msg.id} className={`qa-message ${saved ? 'qa-message-done' : ''}`}>
                            <header className="qa-message-header">
                                <span className="qa-turn-id">{msg.turn_id}</span>
                                <span className="qa-user-id">{msg.user_id}</span>
                            </header>
                            <p className="qa-message-text">{msg.turn_text}</p>

                            <div className="qa-controls">
                                <label className="qa-label-field">
                                    <span>Label</span>
                                    <input
                                        type="text"
                                        value={draft.label}
                                        onChange={(e) => updateDraft(msg.id, { label: e.target.value })}
                                        placeholder="Turn label"
                                    />
                                </label>

                                <div className="qa-flags">
                                    <label>
                                        <input
                                            type="checkbox"
                                            checked={!!draft.trigger_marker}
                                            onChange={(e) => updateDraft(msg.id, { trigger_marker: e.target.checked })}
                                        />
                                        Trigger marker
                                    </label>
                                    <label>
                                        <input
                                            type="checkbox"
                                            checked={!!draft.borderline}
                                            onChange={(e) => updateDraft(msg.id, { borderline: e.target.checked })}
                                        />
                                        Borderline
                                    </label>
                                    <label>
                                        <input
                                            type="checkbox"
                                            checked={!!draft.multiform}
                                            onChange={(e) => updateDraft(msg.id, { multiform: e.target.checked })}
                                        />
                                        Multiform
                                    </label>
                                </div>

                                <button
                                    type="button"
                                    className="qa-save"
                                    disabled={!dirty || savingMessageId === msg.id || !draft.label?.trim()}
                                    onClick={() => saveAnnotation(msg.id)}
                                >
                                    {savingMessageId === msg.id ? 'Saving…' : saved ? 'Update' : 'Save'}
                                </button>
                            </div>
                        </article>
                    );
                })}
            </main>
        </div>
    );
};

export default QuestionAnalysisChatRoom;
