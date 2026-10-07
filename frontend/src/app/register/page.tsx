import { Suspense } from "react";

import { AuthForm } from "@/components/auth-form";

export default function RegisterPage() {
  return (
    <Suspense fallback={<div className="auth-loading" role="status" />}>
      <AuthForm mode="register" />
    </Suspense>
  );
}