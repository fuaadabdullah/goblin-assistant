'use client';

import type { FC } from 'react';
import AgentTaskView from './components/AgentTaskView';
import { useAgentTaskForm } from './hooks/useAgentTaskForm';

const AgentScreen: FC = () => {
  const session = useAgentTaskForm();

  return <AgentTaskView session={session} />;
};

export default AgentScreen;
