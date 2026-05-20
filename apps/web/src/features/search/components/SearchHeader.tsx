interface SearchHeaderProps {
  /** Main headline for the search page. */
  title: string;
  /** Supporting subtitle copy. */
  subtitle: string;
}

const SearchHeader = ({ title, subtitle }: SearchHeaderProps) => (
  <div className="text-center mb-12">
    <h1 className="text-4xl font-bold text-primary mb-3">{title}</h1>
    <p className="text-muted">{subtitle}</p>
  </div>
);

export default SearchHeader;
