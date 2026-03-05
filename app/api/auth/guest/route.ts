// app/api/auth/guest/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { authService } from '../../../lib/services/auth-service';
import { handleApiError, AppError } from '../../../../lib/error-handler';

export async function POST(request: NextRequest) {
  try {
    // Guest login - no credentials required
    const authData = await authService.signInAsGuest();

    if (!authData || !authData.user) {
      throw new AppError('Guest login failed', 500);
    }

    // Create response with proper data structure
    const responseData = {
      success: true,
      message: 'Guest login successful',
      user: {
        id: authData.user.id,
        email: authData.user.email,
        name: authData.user.name,
        isGuest: true,
      },
      session: authData.session,
    };

    // Create response
    const response = NextResponse.json(responseData);

    // Set session cookie if we have a session
    if (authData.session?.access_token) {
      response.cookies.set('auth-token', authData.session.access_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'strict',
        maxAge: 24 * 60 * 60, // 24 hours
        path: '/',
      });
    }

    return response;

  } catch (error) {
    console.error('Guest login API error:', error);
    return handleApiError(error);
  }
}