"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { checkAuth } from "@/lib/api";

interface Props {
  children: React.ReactNode;
}

export function AuthGuard({ children }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const [checking, setChecking] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    // Skip auth check on the login page
    if (pathname === "/login" || pathname === "/login/") {
      setChecking(false);
      setAuthenticated(true);
      return;
    }

    async function verify() {
      const result = await checkAuth();
      if (!result.authenticated) {
        router.replace("/login");
      } else {
        setAuthenticated(true);
      }
      setChecking(false);
    }
    verify();
  }, [pathname, router]);

  if (checking) {
    return (
      <div className="mx-auto max-w-2xl text-center py-12 text-gray-500">
        Loading...
      </div>
    );
  }

  if (!authenticated) {
    return null;
  }

  return <>{children}</>;
}
