import { SignIn } from "@clerk/nextjs";

export default function LoginPage() {
  return (
    <div className="flex min-h-full flex-col items-center justify-center bg-neutral-950 px-4">
      <SignIn
        appearance={{
          elements: {
            rootBox: "mx-auto",
            card: "bg-neutral-900 border border-neutral-800 shadow-xl",
          },
        }}
      />
    </div>
  );
}
