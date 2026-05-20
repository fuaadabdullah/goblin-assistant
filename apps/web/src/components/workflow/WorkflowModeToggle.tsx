import Button from '../ui/Button';

interface Props {
  isBuilderMode: boolean;
  onToggle: () => void;
}

export const WorkflowModeToggle = ({ isBuilderMode, onToggle }: Props) => {
  return (
    <div className="flex items-center justify-between">
      <h3 className="text-lg font-semibold">Workflow Builder</h3>
      <Button variant="secondary" onClick={onToggle}>
        {isBuilderMode ? 'Switch to Text' : 'Switch to Builder'}
      </Button>
    </div>
  );
};
