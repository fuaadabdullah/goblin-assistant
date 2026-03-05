import { useCallback, useState, type DragEvent } from 'react';
import type { ProviderConfig } from '../../../../hooks/api/useSettings';

export const useProviderReorder = ({
  providers,
  onReorder,
}: {
  providers: ProviderConfig[];
  onReorder: (newOrder: ProviderConfig[]) => Promise<void>;
}) => {
  const [draggedProvider, setDraggedProvider] = useState<ProviderConfig | null>(null);

  const handleDragStart = useCallback((provider: ProviderConfig) => {
    setDraggedProvider(provider);
  }, []);

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  }, []);

  const handleDrop = useCallback(
    async (targetProvider: ProviderConfig) => {
      if (!draggedProvider || draggedProvider.id === targetProvider.id) return;

      const newOrder = [...providers];
      const draggedIndex = newOrder.findIndex(p => p.id === draggedProvider.id);
      const targetIndex = newOrder.findIndex(p => p.id === targetProvider.id);

      if (draggedIndex === -1 || targetIndex === -1) return;

      newOrder.splice(draggedIndex, 1);
      newOrder.splice(targetIndex, 0, draggedProvider);

      try {
        await onReorder(newOrder);
      } finally {
        setDraggedProvider(null);
      }
    },
    [draggedProvider, onReorder, providers]
  );

  return {
    draggedProvider,
    handleDragStart,
    handleDragOver,
    handleDrop,
  };
};
