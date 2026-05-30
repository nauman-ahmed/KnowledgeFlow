type UserMessageProps = {
  content: string;
};

export function UserMessage({ content }: UserMessageProps) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] rounded-2xl bg-neutral-800 px-4 py-3 text-[15px] leading-relaxed text-neutral-100">
        {content}
      </div>
    </div>
  );
}
