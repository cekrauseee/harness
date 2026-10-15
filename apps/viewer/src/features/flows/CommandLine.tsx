import { useEffect, useState } from 'react'
import { Check, Copy } from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import { Button } from '@/shared/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/shared/ui/tooltip'

/** A command or URL the reader can select or copy. */
export function CommandLine({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  useEffect(() => {
    if (!copied) return
    const t = setTimeout(() => setCopied(false), 1400)
    return () => clearTimeout(t)
  }, [copied])
  const copy = () =>
    navigator.clipboard?.writeText(text).then(
      () => setCopied(true),
      () => {},
    )
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-2 rounded-lg border bg-background py-1.5 pr-1.5 pl-3">
      <code className="pt-1 font-mono text-[11.5px] leading-relaxed break-all whitespace-pre-wrap select-text">{text}</code>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button variant="ghost" size="icon-sm" onClick={copy} aria-label="Copy" className={cn(copied && 'text-ok')}>
            {copied ? <Check className="animate-in zoom-in-50" /> : <Copy />}
          </Button>
        </TooltipTrigger>
        <TooltipContent>{copied ? 'Copied' : 'Copy'}</TooltipContent>
      </Tooltip>
    </div>
  )
}
