function blocks(content) {
  const parts = String(content).split('```')
  return parts.map((part, index) => {
    if (index % 2 === 1) {
      const newline = part.indexOf('\n')
      const code = newline === -1 ? part : part.slice(newline + 1)
      return { type: 'code', text: code.replace(/\n$/, '') }
    }
    return { type: 'text', text: part }
  })
}

export default function TutorMessage({ content }) {
  return (
    <div className="space-y-2 text-sm leading-relaxed">
      {blocks(content).map((block, index) =>
        block.type === 'code' ? (
          <pre
            key={index}
            className="overflow-x-auto rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs text-foreground"
          >
            <code>{block.text}</code>
          </pre>
        ) : (
          block.text.trim() && (
            <p key={index} className="whitespace-pre-line">
              {block.text.trim()}
            </p>
          )
        ),
      )}
    </div>
  )
}
