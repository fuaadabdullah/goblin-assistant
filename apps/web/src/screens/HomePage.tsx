import HomeScreen from '../features/onboarding/HomeScreen';

const HomePage = () => <HomeScreen />;

// Prevent static generation
export const getServerSideProps = async () => {
  return { props: {} };
};

export default HomePage;
