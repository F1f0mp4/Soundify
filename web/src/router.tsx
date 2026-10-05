/* eslint-disable react-refresh/only-export-components */

import { AmbientBackground } from "@/components/layout/ambient-background";
import { Footer } from "@/components/layout/footer";
import { Header } from "@/components/layout/header";
import { basePath } from "@/lib/base-path";
import { JobsPage } from "@/pages/jobs";
import { SubscriptionsPage } from "@/pages/subscriptions";
import { Toast } from "@heroui/react";
import {
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  useNavigate,
} from "@tanstack/react-router";
import { useEffect } from "react";

function RootLayout() {
  return (
    <>
      <Toast.Provider />
      <AmbientBackground />
      <div className="flex min-h-screen flex-col">
        <Header />
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 pt-4 pb-10 sm:px-6">
          <Outlet />
        </main>
        <Footer />
      </div>
    </>
  );
}

function NotFoundRedirect() {
  const navigate = useNavigate();
  useEffect(() => {
    navigate({ to: "/" });
  }, [navigate]);
  return null;
}

const rootRoute = createRootRoute({
  component: RootLayout,
  notFoundComponent: NotFoundRedirect,
});

const jobsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: JobsPage,
});

const subscriptionsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/playlists",
  component: SubscriptionsPage,
});

const routeTree = rootRoute.addChildren([jobsRoute, subscriptionsRoute]);

export const router = createRouter({ routeTree, basepath: basePath || "/" });
