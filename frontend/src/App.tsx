/**
 * KrishiOS Root Application Component.
 *
 * Composes all global providers (React Query, Auth, Toast) and renders the router tree.
 */

import { RouterProvider } from 'react-router-dom';
import { Providers } from '@/app/providers';
import { router } from '@/app/router';

export default function App() {
  return (
    <Providers>
      <RouterProvider router={router} />
    </Providers>
  );
}
