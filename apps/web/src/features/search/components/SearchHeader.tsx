import { Search } from 'lucide-react';

interface SearchHeaderProps {
  /** Main headline for the search page. */
  title: string;
  /** Supporting subtitle copy. */
  subtitle: string;
}

const SearchHeader = ({ title, subtitle }: SearchHeaderProps) => (
  <div className="text-center mb-12">
    <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary/20 mb-4">
      <Search className="w-7 h-7 text-primary" aria-hidden="true" />
    </div>
    <h1 className="text-4xl font-bold text-primary mb-3">{title}</h1>
    <p className="text-muted max-w-xl mx-auto">{subtitle}</p>
  </div>
);

export default SearchHeader;
