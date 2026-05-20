import React from 'react';
import { formatTitle } from './utils';
import './ModularCard.css';

interface ModularCardProps {
  title: string;
  content: string;
}

export const ModularCard: React.FC<ModularCardProps> = ({ title, content }) => {
  const formatted = formatTitle(title);
  return (
    <div className="modular-card">
      <h4 className="modular-card-title">{formatted}</h4>
      <div className="modular-card-content">{content}</div>
    </div>
  );
};

export default ModularCard;
