// app/api/auth/session/route.ts
import { NextRequest } from 'next/server';
import { authService } from '../../../lib/services/auth-service';
import { handleApiError, createApiResponse, AppError } from 'lib/error-handler';

export async function GET(request: NextRequest) {
  try {
    const authHeader = request.headers.get('authorization');
    const token = authHeader?.replace('Bearer ', '');

    if (!token) {
      throw new AppError('No token provided', 401);
    }

    const user = await authService.validateToken(token);

    if (!user) {
      throw new AppError('Invalid token', 401);
    }

    return createApiResponse({
      user,
      valid: true,
    });
  } catch (error) {
    return handleApiError(error);
  }
}
