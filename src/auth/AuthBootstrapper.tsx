import { useEffect } from 'react';
import { useAuthStore } from '../store/authStore';

const AuthBootstrapper = () => {
    const bootstrapFromSession = useAuthStore(state => state.bootstrapFromSession);

    useEffect(() => {
        bootstrapFromSession();
    }, [bootstrapFromSession]);

    return null;
};

export default AuthBootstrapper;
