import type { FC } from 'react';
import { useSearchResults } from './hooks/useSearchResults';
import SearchView from './components/SearchView';

const SearchScreen: FC = () => {
  const state = useSearchResults();

  return <SearchView state={state} />;
};

export default SearchScreen;
