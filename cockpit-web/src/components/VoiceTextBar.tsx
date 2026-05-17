import { useMemo, useRef, useState } from 'react';
import type { VoiceContext } from '../types';
import { browserSpeechSupported, speakText, startDictation } from '../lib/speech';
import { sendText } from '../lib/api';

interface VoiceTextBarProps {
  context: VoiceContext;
}

export default function VoiceTextBar({ context }: VoiceTextBarProps) {
  const [text, setText] = useState('');
  const [status, setStatus] = useState('Ready');
  const [listening, setListening] = useState(false);
  const [lastReply, setLastReply] = useState('');
  const recognizer = useRef<{ stop: () => void } | null>(null);

  const contextLabel = useMemo(() => {
    if (context.domainId) return `${context.page}: ${context.domainId}`;
    return context.page;
  }, [context]);

  const submit = async (payload: string) => {
    const message = payload.trim();
    if (!message) return;

    setStatus('Sending…');
    try {
      const response = await sendText(message, context);
      setLastReply(response.reply);
      setStatus('Rook replied');
      speakText(response.reply);
      setText('');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Failed to send');
    }
  };

  const toggleListening = () => {
    if (listening) {
      recognizer.current?.stop();
      recognizer.current = null;
      setListening(false);
      setStatus('Stopped listening');
      return;
    }

    setListening(true);
    setStatus('Listening…');
    recognizer.current = startDictation({
      onTranscript: async (transcript) => {
        setText(transcript);
        await submit(transcript);
      },
      onError: (message) => {
        setStatus(message);
      },
      onEnd: () => {
        setListening(false);
      }
    });
  };

  return (
    <div className="voice-bar" role="region" aria-label="Voice and text command bar">
      <button className="voice-bar__mic" onClick={toggleListening} type="button">
        {listening ? '⏹️' : '🎙️'}
      </button>
      <input
        className="voice-bar__input"
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="Talk to Rook or type a command"
        onKeyDown={(event) => {
          if (event.key === 'Enter') void submit(text);
        }}
      />
      <button className="voice-bar__send" type="button" onClick={() => void submit(text)}>
        Send
      </button>
      <div className="voice-bar__meta">
        <span>Context: {contextLabel}</span>
        <span>{browserSpeechSupported() ? status : 'Voice unavailable in this browser'}</span>
        {lastReply ? <span className="voice-bar__reply">Rook: {lastReply}</span> : null}
      </div>
    </div>
  );
}
