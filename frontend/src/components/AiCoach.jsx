import { useState, useRef, useEffect } from 'react';
import { aiCoachApi } from '../lib/api';

/**
 * AI Coach Chatbot Panel
 *
 * A slide-up chatbot overlay powered by Gemini 2.5 Flash.
 * Gets full context from the user's profile + analyzed workout data.
 * Session-only — no persistence across reloads.
 */
export default function AiCoach({ workoutId, workoutData, onClose }) {
  const [messages, setMessages] = useState([
    {
      role: 'model',
      content: `Hey! 👋 I'm your AI Coach. I've reviewed your **${workoutData?.workout_type || 'workout'}** session — rated **${workoutData?.effectiveness_name || 'N/A'}** effectiveness.\n\nAsk me anything about your training, recovery, or how to improve!`,
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    setTimeout(() => inputRef.current?.focus(), 300);
  }, []);

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    const userMessage = { role: 'user', content: trimmed };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInput('');
    setLoading(true);

    try {
      // Build history (skip the initial greeting)
      const history = updatedMessages
        .slice(1, -1) // exclude greeting and the message we just sent
        .map((m) => ({ role: m.role, content: m.content }));

      const response = await aiCoachApi.chat(workoutId, trimmed, history);

      setMessages((prev) => [
        ...prev,
        { role: 'model', content: response.reply },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'model',
          content: `⚠️ Sorry, I encountered an error: ${err.message}. Please try again.`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Simple markdown-ish rendering: bold and line breaks
  const renderContent = (text) => {
    return text.split('\n').map((line, i) => {
      // Bold **text**
      const parts = line.split(/(\*\*.*?\*\*)/g).map((part, j) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={j}>{part.slice(2, -2)}</strong>;
        }
        return part;
      });
      return (
        <span key={i}>
          {parts}
          {i < text.split('\n').length - 1 && <br />}
        </span>
      );
    });
  };

  return (
    <div className="ai-coach-overlay" onClick={onClose}>
      <div className="ai-coach-panel" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="ai-coach-header">
          <div className="ai-coach-title">
            <div className="ai-coach-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <div>
              <h3>AI Coach</h3>
              <span className="ai-coach-subtitle">{workoutData?.workout_type || 'Workout'}</span>
            </div>
          </div>
          <button className="ai-coach-close" onClick={onClose} title="Close AI Coach">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Messages */}
        <div className="ai-coach-messages">
          {messages.map((msg, i) => (
            <div key={i} className={`ai-coach-msg ${msg.role === 'user' ? 'user-msg' : 'model-msg'}`}>
              {msg.role === 'model' && (
                <div className="msg-avatar">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                  </svg>
                </div>
              )}
              <div className="msg-bubble">
                {renderContent(msg.content)}
              </div>
            </div>
          ))}

          {/* Typing indicator */}
          {loading && (
            <div className="ai-coach-msg model-msg">
              <div className="msg-avatar">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                </svg>
              </div>
              <div className="msg-bubble typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="ai-coach-input-area">
          <textarea
            ref={inputRef}
            className="ai-coach-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your workout..."
            rows={1}
            disabled={loading}
          />
          <button
            className="ai-coach-send"
            onClick={sendMessage}
            disabled={!input.trim() || loading}
            title="Send message"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
