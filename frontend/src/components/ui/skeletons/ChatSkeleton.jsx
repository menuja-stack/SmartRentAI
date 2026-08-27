import React from 'react';
import { Bar, Circle } from './Skeleton';

/** Alternating chat-bubble placeholders (bot left, user right). */
export default function ChatSkeleton({ bubbles = 4 }) {
  return (
    <div className="p-4 space-y-4">
      {[...Array(bubbles)].map((_, i) => {
        const isUser = i % 2 === 1;
        return (
          <div key={i} className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
            {!isUser && <Circle size="w-8 h-8" />}
            <div className={`space-y-2 ${isUser ? 'items-end' : ''}`}>
              <Bar className={`h-10 rounded-2xl ${isUser ? 'w-40' : 'w-56'}`} />
            </div>
            {isUser && <Circle size="w-8 h-8" />}
          </div>
        );
      })}
    </div>
  );
}
