/**
 * @fileoverview Annotator interface for the ``question_analysis`` project type.
 *
 * Renders each chat turn with a compact annotation panel: a free-form ``label``
 * input, a two-level trigger-marker section (primary check + 5 secondary
 * features), and two boolean flags (``borderline``, ``multiform``).
 *
 * Interactive features:
 * - Click on a user badge to highlight / toggle all turns by that speaker.
 * - Hover over the reply indicator (↪) to highlight both the current turn and
 *   the turn it replies to.
 *
 * One persisted row per (message, annotator) pair; the backend upserts on POST.
 * ``trigger_marker`` is derived server-side from the breakdown fields.
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

const EMPTY_DRAFT = {
    label: '',
    trigger_primary: false,
    trigger_f2: false,
    trigger_f3: false,
    trigger_f4: false,
    trigger_f5: false,
    trigger_f6: false,
    borderline: false,
    multiform: false,
};

/** Secondary features shown in the trigger breakdown (indices match f2–f6). */
const SECONDARY_FEATURES = [
    { key: 'trigger_f2', label: 'Bare interrogative fragment', hint: 'e.g. "Porquê", "Como assim"' },
    { key: 'trigger_f3', label: 'Turn-initial wh-word', hint: 'Matrix use only — not relative/embedded' },
    { key: 'trigger_f4', label: 'Dedicated interrogative construction', hint: 'será que… / não será (que)…' },
    { key: 'trigger_f5', label: 'Disjunctive choice question', hint: 'e.g. "Universal ou diversa"' },
    { key: 'trigger_f6', label: 'Conventionalised formula', hint: 'e.g. "alguém sabe…", "o que acham"' },
];

/** Extract the reply-to turn id from a message, trying multiple field names. */
const getReplyTo = (msg) =>
    msg.reply_to_turn || msg.reply_to || msg.reply_to_id || null;

const QuestionAnalysisChatRoom = () => {
    const { projectId, roomId } = useParams();
    const navigate = useNavigate();

    const [messages, setMessages] = useState([]);
    const [annotationsByMessage, setAnnotationsByMessage] = useState({});
    const [currentUser, setCurrentUser] = useState(null);
    const [chatRoomName, setChatRoomName] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [savingMessageId, setSavingMessageId] = useState(null);
    const [clearingMessageId, setClearingMessageId] = useState(null);
    const [showRubric, setShowRubric] = useState(false);
    const [isCompleted, setIsCompleted] = useState(false);
    const [isCompletionSaving, setIsCompletionSaving] = useState(false);

    // Hover / highlight interaction state
    const [highlightedUserId, setHighlightedUserId] = useState(null);
    const [replyHoverIds, setReplyHoverIds] = useState(null); // Set<number>

    // Accordion expand state — empty Set means all collapsed
    const [expandedIds, setExpandedIds] = useState(new Set());

    const [drafts, setDrafts] = useState({});

    const fetchData = useCallback(async () => {
        if (!projectId || !roomId) return;
        setLoading(true);
        setError(null);
        try {
            const [roomData, messagesResponse, userData, qaRows, completionData] = await Promise.all([
                projectsApi.getChatRoom(projectId, roomId),
                projectsApi.getChatMessages(projectId, roomId),
                auth.getCurrentUser(),
                qaApi.getChatRoomAnnotations(projectId, roomId),
                projectsApi.getChatRoomCompletion(projectId, roomId),
            ]);
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
                        trigger_primary: !!row.trigger_primary,
                        trigger_f2: !!row.trigger_f2,
                        trigger_f3: !!row.trigger_f3,
                        trigger_f4: !!row.trigger_f4,
                        trigger_f5: !!row.trigger_f5,
                        trigger_f6: !!row.trigger_f6,
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

    /** Map turn_id → message.id for reply-hover resolution. */
    const turnIdToMsgId = useMemo(() => {
        const map = {};
        messages.forEach(m => { map[m.turn_id] = m.id; });
        return map;
    }, [messages]);

    // -------------------------------------------------------------------------
    // Interaction handlers
    // -------------------------------------------------------------------------

    /** Toggle persistent user highlight. Clears if same user clicked again. */
    const handleUserClick = (userId) => {
        setHighlightedUserId(prev => (prev === userId ? null : userId));
    };

    /** Highlight the hovered message + its reply target (if any). */
    const handleReplyHover = (currentMsgId, replyToTurnId) => {
        const targetId = turnIdToMsgId[replyToTurnId];
        if (!targetId) return;
        setReplyHoverIds(new Set([currentMsgId, targetId]));
    };

    const handleReplyHoverEnd = () => setReplyHoverIds(null);

    const toggleExpand = (msgId) => {
        setExpandedIds(prev => {
            const next = new Set(prev);
            next.has(msgId) ? next.delete(msgId) : next.add(msgId);
            return next;
        });
    };

    const expandAll = () => setExpandedIds(new Set(messages.map(m => m.id)));
    const collapseAll = () => setExpandedIds(new Set());
    const allExpanded = messages.length > 0 && expandedIds.size === messages.length;

    // -------------------------------------------------------------------------
    // Annotation handlers
    // -------------------------------------------------------------------------

    const updateDraft = (messageId, patch) => {
        setDrafts(prev => ({
            ...prev,
            [messageId]: {
                ...EMPTY_DRAFT,
                ...(prev[messageId] || {}),
                ...patch,
            },
        }));
    };

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
                trigger_primary: !!draft.trigger_primary,
                trigger_f2: !!draft.trigger_f2,
                trigger_f3: !!draft.trigger_f3,
                trigger_f4: !!draft.trigger_f4,
                trigger_f5: !!draft.trigger_f5,
                trigger_f6: !!draft.trigger_f6,
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

    /** Delete the saved annotation and reset the draft to empty. */
    const clearAnnotation = async (messageId) => {
        const saved = annotationsByMessage[messageId];
        if (!saved) return;
        setClearingMessageId(messageId);
        try {
            await qaApi.deleteAnnotation(projectId, roomId, saved.id);
            setAnnotationsByMessage(prev => {
                const next = { ...prev };
                delete next[messageId];
                return next;
            });
            setDrafts(prev => ({ ...prev, [messageId]: { ...EMPTY_DRAFT } }));
        } catch (err) {
            console.error('Clear error:', err);
            setError(parseApiError(err));
        } finally {
            setClearingMessageId(null);
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
                        onClick={allExpanded ? collapseAll : expandAll}
                    >
                        {allExpanded ? 'Collapse all' : 'Expand all'}
                    </button>
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
                        <p><strong>Primary check (1)</strong> — the turn carries a question mark.</p>
                        <p><strong>No question mark?</strong> Mark any secondary features that apply:</p>
                        <ol start="2">
                            {SECONDARY_FEATURES.map((f) => (
                                <li key={f.key}>
                                    <strong>{f.label}</strong> — {f.hint}
                                </li>
                            ))}
                        </ol>
                        <button onClick={() => setShowRubric(false)}>Close</button>
                    </div>
                </Modal>
            )}

            <main className="qa-messages">
                {messages.map((msg) => {
                    const draft = drafts[msg.id] || { ...EMPTY_DRAFT };
                    const saved = annotationsByMessage[msg.id];
                    const replyTo = getReplyTo(msg);

                    const isExpanded = expandedIds.has(msg.id);
                    const isUserHighlighted = highlightedUserId === msg.user_id;
                    const isReplyLinked = replyHoverIds ? replyHoverIds.has(msg.id) : false;

                    const dirty = !saved
                        || saved.label !== draft.label.trim()
                        || !!saved.trigger_primary !== !!draft.trigger_primary
                        || !!saved.trigger_f2 !== !!draft.trigger_f2
                        || !!saved.trigger_f3 !== !!draft.trigger_f3
                        || !!saved.trigger_f4 !== !!draft.trigger_f4
                        || !!saved.trigger_f5 !== !!draft.trigger_f5
                        || !!saved.trigger_f6 !== !!draft.trigger_f6
                        || !!saved.borderline !== !!draft.borderline
                        || !!saved.multiform !== !!draft.multiform;

                    const articleClass = [
                        'qa-message',
                        saved ? 'qa-message-done' : '',
                        isUserHighlighted ? 'qa-user-highlighted' : '',
                        isReplyLinked ? 'qa-reply-linked' : '',
                        !isExpanded ? 'qa-message-collapsed' : '',
                    ].filter(Boolean).join(' ');

                    return (
                        <article
                            key={msg.id}
                            className={articleClass}
                            data-message-id={msg.id}
                            onClick={!isExpanded ? () => toggleExpand(msg.id) : undefined}
                        >
                            <header className="qa-message-header">
                                <span className="qa-turn-id">{msg.turn_id}</span>
                                <span
                                    className={`qa-user-id ${isUserHighlighted ? 'qa-user-id-active' : ''}`}
                                    onClick={(e) => { e.stopPropagation(); handleUserClick(msg.user_id); }}
                                    title="Click to highlight all turns by this user"
                                >
                                    {msg.user_id}
                                </span>
                                {replyTo && (
                                    <span
                                        className="qa-reply-indicator"
                                        onMouseEnter={() => handleReplyHover(msg.id, replyTo)}
                                        onMouseLeave={handleReplyHoverEnd}
                                        title={`Replies to turn ${replyTo}`}
                                    >
                                        ↪ {replyTo}
                                    </span>
                                )}
                                {!isExpanded && saved && (
                                    <span className="qa-status-chip">{saved.label}</span>
                                )}
                                {!isExpanded && !saved && (
                                    <span className="qa-status-dot" />
                                )}
                                <button
                                    type="button"
                                    className="qa-toggle-btn"
                                    onClick={(e) => { e.stopPropagation(); toggleExpand(msg.id); }}
                                    title={isExpanded ? 'Collapse' : 'Expand'}
                                >
                                    {isExpanded ? '⌃' : '⌄'}
                                </button>
                            </header>
                            <p className="qa-message-text">{msg.turn_text}</p>

                            {isExpanded && <div className="qa-controls" onClick={(e) => e.stopPropagation()}>
                                <label className="qa-label-field">
                                    <span>Label</span>
                                    <input
                                        type="text"
                                        value={draft.label}
                                        onChange={(e) => updateDraft(msg.id, { label: e.target.value })}
                                        placeholder="Turn label"
                                    />
                                </label>

                                <div className="qa-trigger-section">
                                    <label className="qa-trigger-primary">
                                        <input
                                            type="checkbox"
                                            checked={!!draft.trigger_primary}
                                            onChange={(e) => updateDraft(msg.id, { trigger_primary: e.target.checked })}
                                        />
                                        <strong>Trigger (1)</strong> — question mark present
                                    </label>
                                    <div className="qa-trigger-secondary">
                                        <span className="qa-secondary-label">No ? — secondary features:</span>
                                        {SECONDARY_FEATURES.map((f) => (
                                            <label key={f.key} title={f.hint}>
                                                <input
                                                    type="checkbox"
                                                    checked={!!draft[f.key]}
                                                    onChange={(e) => updateDraft(msg.id, { [f.key]: e.target.checked })}
                                                />
                                                {f.label}
                                            </label>
                                        ))}
                                    </div>
                                </div>

                                <div className="qa-flags">
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

                                <div className="qa-actions">
                                    <button
                                        type="button"
                                        className="qa-save"
                                        disabled={!dirty || savingMessageId === msg.id || !draft.label?.trim()}
                                        onClick={() => saveAnnotation(msg.id)}
                                    >
                                        {savingMessageId === msg.id ? 'Saving…' : saved ? 'Update' : 'Save'}
                                    </button>
                                    {saved && (
                                        <button
                                            type="button"
                                            className="qa-clear"
                                            disabled={clearingMessageId === msg.id}
                                            onClick={() => clearAnnotation(msg.id)}
                                        >
                                            {clearingMessageId === msg.id ? 'Clearing…' : 'Clear'}
                                        </button>
                                    )}
                                </div>
                            </div>}
                        </article>
                    );
                })}
            </main>
        </div>
    );
};

export default QuestionAnalysisChatRoom;
