"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";

type ErrorBoundaryProps = {
  children: ReactNode;
  fallback?: ReactNode;
};

type ErrorBoundaryState = {
  hasError: boolean;
  message: string | null;
};

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, message: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, message: error.message };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 text-center">
          <p className="text-sm font-medium text-neutral-200">Something went wrong</p>
          <p className="max-w-md text-xs text-neutral-500">
            {this.state.message ?? "An unexpected error occurred. Try refreshing the page."}
          </p>
          <button
            type="button"
            onClick={() => this.setState({ hasError: false, message: null })}
            className="rounded-lg border border-neutral-600 px-3 py-1.5 text-xs text-neutral-300 hover:bg-neutral-800"
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
