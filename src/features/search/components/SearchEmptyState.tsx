interface SearchEmptyStateProps {
  /** Icon emoji to display. */
  icon: string;
  /** Headline text. */
  title: string;
  /** Supporting description. */
  description: string;
}

const SearchEmptyState = ({ icon, title, description }: SearchEmptyStateProps) => (
  <div className="text-center py-16">
    <div className="w-20 h-20 bg-surface-hover rounded-full flex items-center justify-center mx-auto mb-4">
      <span className="text-4xl">{icon}</span>
    </div>
    <h3 className="text-lg font-medium text-text mb-2">{title}</h3>
    <p className="text-muted">{description}</p>
  </div>
);

export default SearchEmptyState;
