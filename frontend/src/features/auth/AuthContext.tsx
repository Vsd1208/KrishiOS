/**
 * Authentication Context and Provider for KrishiOS.
 *
 * Manages user session state, JWT decoding, token refresh on mount,
 * and exposes login/logout operations to the entire component tree.
 */

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  type ReactNode,
} from 'react';
import type { AuthUser, LoginRequest, TokenResponse, JwtPayload } from '@/types/auth';
import { login as apiLogin, refreshTokens as apiRefreshTokens, logout as apiLogout } from '@/services/api/auth';
import { getRefreshToken } from '@/services/api/client';

export interface AuthContextType {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginRequest) => Promise<TokenResponse>;
  loginFn: (credentials: LoginRequest) => Promise<TokenResponse>;
  logout: () => Promise<void>;
  logoutFn: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * Decodes the payload section of a JWT access token using atob().
 * Handles URL-safe base64 encoding without third-party dependencies.
 */
function decodeJwtPayload(token: string): AuthUser | null {
  try {
    const parts = token.split('.');
    if (parts.length < 2 || !parts[1]) {
      return null;
    }

    // Convert base64url to standard base64
    let base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    while (base64.length % 4 !== 0) {
      base64 += '=';
    }

    // Decode and parse JSON
    const decodedString = atob(base64);
    const payload: JwtPayload = JSON.parse(decodedString);

    if (!payload.sub || !payload.role) {
      return null;
    }

    return {
      uuid: payload.sub,
      role: payload.role,
      permissions: payload.permissions ?? [],
    };
  } catch (error) {
    console.error('Failed to decode JWT token payload:', error);
    return null;
  }
}

export interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Initialize session on mount by checking for an existing refresh token
  useEffect(() => {
    let isMounted = true;

    async function initSession() {
      const existingRefreshToken = getRefreshToken();
      if (!existingRefreshToken) {
        if (isMounted) {
          setIsLoading(false);
        }
        return;
      }

      try {
        const tokenResponse = await apiRefreshTokens();
        if (isMounted) {
          if (tokenResponse?.access_token) {
            const decodedUser = decodeJwtPayload(tokenResponse.access_token);
            setUser(decodedUser);
          } else {
            setUser(null);
          }
        }
      } catch (err) {
        console.warn('Session restoration failed:', err);
        if (isMounted) {
          setUser(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    initSession();

    return () => {
      isMounted = false;
    };
  }, []);

  const loginFn = useCallback(async (credentials: LoginRequest): Promise<TokenResponse> => {
    setIsLoading(true);
    try {
      const response = await apiLogin(credentials);
      const decodedUser = decodeJwtPayload(response.access_token);
      if (!decodedUser) {
        throw new Error('Invalid token payload received from server');
      }
      setUser(decodedUser);
      return response;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logoutFn = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    try {
      await apiLogout();
    } finally {
      setUser(null);
      setIsLoading(false);
    }
  }, []);

  const contextValue = useMemo<AuthContextType>(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isLoading,
      login: loginFn,
      loginFn,
      logout: logoutFn,
      logoutFn,
    }),
    [user, isLoading, loginFn, logoutFn],
  );

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
};

/**
 * Hook to access authentication context.
 * Throws an error if used outside an AuthProvider.
 */
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
