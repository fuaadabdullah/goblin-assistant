// src/components/ProviderDropdown.tsx
import { useProviderRouter } from "../hooks/useProviderRouter";

export function ProviderDropdown({ capability, onSelect }: { capability: string; onSelect: (pid: string)=>void }) {
  const { topProviders } = useProviderRouter();
  const options = topProviders(capability, true, false, 6);
  return (
    <select title="Select AI provider" onChange={(e)=> onSelect(e.target.value)} defaultValue={options[0]}>
      {options.map(pid => <option key={pid} value={pid}>{pid}</option>)}
    </select>
  );
}
