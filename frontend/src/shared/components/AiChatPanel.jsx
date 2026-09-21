import { useState, useRef, useEffect } from 'react'
import PropTypes from 'prop-types'
import {
  Sparkles,
  Send,
  X,
  Bot,
  RotateCcw,
  ExternalLink,
  ChevronRight,
  MessageSquare
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Separator } from '@/components/ui/separator'
import { useAuth } from '../auth/useAuth.js'

const SUGGESTED_PROMPTS = [
  'What are my next project milestones?',
  'Summarize recent thesis submissions',
  'Review rubric guidelines for Phase 2',
  'Generate an outline for research proposal'
]

const INITIAL_MESSAGES = [
  {
    id: 'msg-welcome-1',
    role: 'assistant',
    content: "👋 Hello! I'm your EduFlow Academic & Research Copilot. How can I assist with your projects, grading, or milestone tracking today?",
    time: 'Just now'
  }
]

let messageIdCounter = 0
function generateMessageId(prefix) {
  messageIdCounter += 1
  return `${prefix}-${messageIdCounter}`
}

export default function AiChatPanel({ onClose }) {
  const { user } = useAuth()
  const [messages, setMessages] = useState(INITIAL_MESSAGES)
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping])

  const handleSendMessage = (textToSend) => {
    const text = (typeof textToSend === 'string' ? textToSend : inputValue).trim()
    if (!text) return

    const userMessage = {
      id: generateMessageId('user'),
      role: 'user',
      content: text,
      time: 'Just now'
    }

    setMessages((prev) => [...prev, userMessage])
    setInputValue('')
    setIsTyping(true)

    setTimeout(() => {
      let botReply = `I understand you are asking about "${text}". Based on your role (${user?.role || 'user'}), I can help organize deadlines, analyze research progress, and evaluate submission rubrics.`
      if (text.toLowerCase().includes('milestone')) {
        botReply = 'Your upcoming project milestone is **Phase 2: System Architecture & Data Pipeline**, scheduled for review next Monday. Would you like a preparation checklist?'
      } else if (text.toLowerCase().includes('rubric')) {
        botReply = 'The Phase 2 evaluation rubric weights:\n- Architecture & Scalability: 35%\n- Implementation Quality: 35%\n- Presentation & Q&A: 30%'
      }

      setMessages((prev) => [
        ...prev,
        {
          id: generateMessageId('bot'),
          role: 'assistant',
          content: botReply,
          time: 'Just now'
        }
      ])
      setIsTyping(false)
    }, 800)
  }

  const handleResetChat = () => {
    setMessages(INITIAL_MESSAGES)
    setIsTyping(false)
  }

  return (
    <aside aria-label="AI Copilot" className="flex flex-col h-full w-full bg-card select-none overflow-hidden">
      {/* Header (Fixed to top of panel) */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-card/80 backdrop-blur shrink-0">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary border border-primary/20">
            <Sparkles className="h-4 w-4" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5">
              <span className="text-sm font-semibold tracking-tight text-foreground">AI Copilot</span>
              <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4 font-normal">
                Beta
              </Badge>
            </div>
            <span className="text-[11px] text-muted-foreground">EduFlow Assistant</span>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground hover:text-foreground cursor-pointer"
            onClick={handleResetChat}
            title="Reset conversation"
          >
            <RotateCcw className="h-4 w-4" />
          </Button>

          {onClose && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-muted-foreground hover:text-foreground cursor-pointer"
              onClick={onClose}
              title="Close AI Copilot"
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Message List (ONLY this section scrolls) */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4 text-xs select-text column-scroll-contain">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex items-start gap-2.5 animate-fade-rise ${
              msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'
            }`}
          >
            {msg.role === 'assistant' ? (
              <div className="flex h-7 w-7 shrink-0 select-none items-center justify-center rounded-md bg-primary text-primary-foreground shadow-xs">
                <Bot className="h-4 w-4" />
              </div>
            ) : (
              <Avatar className="h-7 w-7 shrink-0 text-xs">
                <AvatarFallback className="bg-muted font-medium text-foreground">
                  {user?.name ? user.name.slice(0, 2).toUpperCase() : 'ME'}
                </AvatarFallback>
              </Avatar>
            )}

            <div
              className={`flex flex-col gap-1 max-w-[82%] ${
                msg.role === 'user' ? 'items-end' : 'items-start'
              }`}
            >
              <div
                className={`rounded-2xl px-3.5 py-2.5 leading-relaxed shadow-xs text-xs whitespace-pre-line ${
                  msg.role === 'user'
                    ? 'bg-primary text-primary-foreground rounded-tr-none'
                    : 'bg-muted/70 text-foreground border border-border/60 rounded-tl-none'
                }`}
              >
                {msg.content}
              </div>
              <span className="text-[10px] text-muted-foreground px-1">{msg.time}</span>
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="flex items-start gap-2.5 animate-fade-rise">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground shadow-xs">
              <Bot className="h-4 w-4" />
            </div>
            <div className="rounded-2xl bg-muted/70 border border-border/60 px-3.5 py-2 text-muted-foreground rounded-tl-none flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-primary/70 animate-bounce" />
              <span className="h-1.5 w-1.5 rounded-full bg-primary/70 animate-bounce [animation-delay:0.2s]" />
              <span className="h-1.5 w-1.5 rounded-full bg-primary/70 animate-bounce [animation-delay:0.4s]" />
            </div>
          </div>
        )}

        {/* Suggested Prompts (contained within scrollable area) */}
        {messages.length <= 2 && !isTyping && (
          <div className="pt-2">
            <p className="text-[11px] font-medium text-muted-foreground mb-1.5 flex items-center gap-1">
              <MessageSquare className="h-3 w-3" />
              Suggested questions
            </p>
            <div className="flex flex-col gap-1">
              {SUGGESTED_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => handleSendMessage(prompt)}
                  className="text-left text-[11px] px-2.5 py-1.5 rounded-md bg-muted/50 hover:bg-muted text-foreground/80 hover:text-foreground border border-border/40 transition-all duration-150 active:scale-[0.98] flex items-center justify-between group cursor-pointer"
                >
                  <span className="truncate">{prompt}</span>
                  <ChevronRight className="h-3 w-3 text-muted-foreground group-hover:translate-x-0.5 transition-transform duration-150" />
                </button>
              ))}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <Separator className="shrink-0" />

      {/* Input Form (Fixed to bottom of panel) */}
      <div className="p-3 bg-card shrink-0">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            handleSendMessage()
          }}
          className="flex items-center gap-1.5 relative"
        >
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Ask AI Copilot anything..."
            className="h-10 text-xs pr-10 bg-muted/40"
            disabled={isTyping}
          />
          <Button
            type="submit"
            size="icon"
            disabled={!inputValue.trim() || isTyping}
            className="absolute right-1 top-1 h-8 w-8 shrink-0 rounded-md cursor-pointer"
          >
            <Send className="h-3.5 w-3.5" />
          </Button>
        </form>
        <p className="text-[10px] text-muted-foreground text-center mt-1.5 flex items-center justify-center gap-1">
          <span>EduFlow Copilot is experimental.</span>
          <span className="underline cursor-pointer hover:text-foreground inline-flex items-center gap-0.5">
            Privacy info <ExternalLink className="h-2.5 w-2.5" />
          </span>
        </p>
      </div>
    </aside>
  )
}

AiChatPanel.propTypes = {
  onClose: PropTypes.func
}
