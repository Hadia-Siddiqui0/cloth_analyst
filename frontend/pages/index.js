import { useEffect } from "react";
import { useRouter } from "next/router";

// Landing page just routes to the right place based on auth state --
// the real "hello world" deploy check from Day 4 has served its purpose
// now that there's an actual app to route into.
export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const hasToken =
      typeof window !== "undefined" && localStorage.getItem("access_token");
    router.replace(hasToken ? "/dashboard" : "/login");
  }, [router]);

  return null;
}
