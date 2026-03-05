// app/api/auth/logout/route.ts
import { authService } from '../../../lib/services/auth-service';
import { handleApiError, createApiResponse } from 'lib/error-handler';

export async function POST() {
  try {
    await authService.signOut();

    return createApiResponse({
      success: true,
      message: 'Logged out successfully',
    });
  } catch (error) {
    return handleApiError(error);
  }
}
