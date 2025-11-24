import { useState, useEffect, useRef } from "react";
import "./StreamingView.css";

interface Props {
	streamingText: string;
	isStreaming?: boolean;
}

interface TokenChunk {
	text: string;
	isCode: boolean;
	timestamp: number;
}

export default function StreamingView({ streamingText, isStreaming = false }: Props) {
	const [tokens, setTokens] = useState<TokenChunk[]>([]);
	const [currentText, setCurrentText] = useState("");
	const streamingRef = useRef<HTMLDivElement>(null);
	const lastChunkRef = useRef<string>("");

	useEffect(() => {
		// Always update current text
		setCurrentText(streamingText);

		// Only process new chunks when streaming
		if (!isStreaming) {
			return;
		}

		const newChunk = streamingText.slice(lastChunkRef.current.length);
		if (newChunk) {
			const newToken: TokenChunk = {
				text: newChunk,
				isCode: streamingText.includes("```") || streamingText.includes("`"),
				timestamp: Date.now()
			};

			setTokens(prev => [...prev, newToken]);
			lastChunkRef.current = streamingText;
		}
	}, [streamingText, isStreaming]);

	useEffect(() => {
		// Auto-scroll to bottom when new content arrives
		if (streamingRef.current) {
			streamingRef.current.scrollTop = streamingRef.current.scrollHeight;
		}
	}, [currentText]);

	const renderTokenizedContent = () => {
		if (!isStreaming) {
			return <pre className="streaming-output">{currentText}</pre>;
		}

		return (
			<div className="streaming-output tokenized">
				{tokens.map((token, index) => (
					<span
						key={index}
						className={`token ${token.isCode ? 'code-token' : 'text-token'}`}
						style={{
							animationDelay: `${index * 20}ms`,
							opacity: 0,
							animation: 'fadeInToken 0.3s ease-in forwards'
						}}
					>
						{token.text}
					</span>
				))}
			</div>
		);
	};

	return (
		<div className="streaming-view" aria-live="polite" data-testid="streaming-view">
			<div className="streaming-header" data-testid="streaming-header">
				<h3 data-testid="streaming-title">Streaming Output</h3>
				{isStreaming && <div className="streaming-indicator" data-testid="streaming-indicator">● Streaming</div>}
			</div>
			<div className="streaming-container" ref={streamingRef} data-testid="streaming-container">
				{renderTokenizedContent()}
			</div>
		</div>
	);
}
