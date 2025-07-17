import React, { useState, useRef, useEffect } from "react";
import {
  Send,
  Moon,
  Sun,
  Circle,
  CheckCircle2,
  Sparkles,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import ReactMarkdown from "react-markdown";
import rehypeRaw from "rehype-raw";
import type { Pluggable } from "unified";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import type { Message, ChatMessage, ToolCall } from "@/lib/types";
import { apiClient } from "@/lib/api";
import { generateId, formatTimestamp } from "@/lib/utils";
import ToolCallDisplay from "./ToolCallDisplay";
import DisclaimerDialog from "./DisclaimerDialog";

// Helper: replace <plan>...</plan> with <details><summary>行動計畫 (Plan)</summary>...</details>
const transformPlanTags = (text: string) => {
  // Keep the details element open while the <plan> section is still streaming.
  // As soon as the closing </plan> tag is present, remove the "open" attribute so it collapses automatically.
  const shouldKeepOpen = !text.includes("</plan>");
  const openAttr = shouldKeepOpen ? " open" : "";

  return text
    .replace(
      /<plan>/g,
      `<details${openAttr}><summary>行動計畫 (Plan)</summary>\n`
    )
    .replace(/<\/plan>/g, "</details>");
};

const rehypeRawPlugin: Pluggable = rehypeRaw as unknown as Pluggable;
const rehypeHighlightPlugin: Pluggable =
  rehypeHighlight as unknown as Pluggable;

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      text: "**LyBot**\n我是您的立法院研究助理！\n\n🟢 **我能幫您什麼？**\n以「立委在各類會議中的實際發言」為核心，快速搜尋並提供逐字稿、影片等原始資料。\n- 精準定位與「事件、主題、法案、預算案」相關的質詢與發言內容\n\n🔴 **我暫時不擅長的事**\n- 需要精確計數或統計的問題（例如：出席率、提案數量排行）\n  此類需求請仍以立法院官方資料為準。\n\n請自由發問！\n\n> 使用前，請先閱讀 [免責聲明](#disclaimer)。繼續使用即表示您已閱讀並同意相關條款。\n\n**注意**：由於 AI 特性與開發時間限制，仍有出錯可能，請善用回應中的連結自行查證。\n\n**目前僅支援第 11 屆立委**\n\n若有任何問題，歡迎來信： ly@codeer.ai\n\n(若對 AI 回應有疑問，請附「您的提問截圖」及「AI 回應截圖」）",
      sender: "assistant",
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isDark, setIsDark] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const toggleTheme = () => {
    setIsDark(!isDark);
  };

  useEffect(() => {
    const root = window.document.documentElement;
    if (isDark) {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }, [isDark]);

  const handleSendMessage = async () => {
    if (inputValue.trim() === "" || isLoading) return;

    const newMessage: Message = {
      id: generateId(),
      text: inputValue,
      sender: "user",
      timestamp: new Date(),
      status: "sending",
    };

    setMessages((prev) => [...prev, newMessage]);
    setInputValue("");
    setIsLoading(true);
    setIsStreaming(true);

    setTimeout(() => {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === newMessage.id ? { ...msg, status: "sent" } : msg
        )
      );
    }, 200);

    try {
      const chatMessages: ChatMessage[] = [...messages, newMessage].map(
        (msg) => {
          if (msg.sender === "user") {
            return { role: "user" as const, content: msg.text };
          } else if (msg.sender === "assistant") {
            return {
              role: "assistant" as const,
              content: msg.text,
              ...(msg.toolCalls ? { tool_calls: msg.toolCalls } : {}),
            };
          } else if (msg.sender === "tool") {
            return {
              role: "tool" as const,
              content: msg.text,
              tool_call_id: msg.toolCallId,
            };
          }
          // Fallback
          return { role: "assistant" as const, content: msg.text };
        }
      );

      const assistantMessageId = generateId();
      let assistantContent = "";

      setMessages((prev) => [
        ...prev,
        {
          id: assistantMessageId,
          text: "",
          sender: "assistant",
          timestamp: new Date(),
        },
      ]);

      try {
        let accumulatedToolCalls: ToolCall[] = [];
        let toolCallsComplete = false;

        for await (const chunk of apiClient.chatCompletionStream(
          chatMessages
        )) {
          if (chunk.tool_calls) {
            // Accumulate tool calls
            accumulatedToolCalls = [
              ...accumulatedToolCalls,
              ...chunk.tool_calls,
            ];

            // Update message with tool calls
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? {
                      ...msg,
                      toolCalls: accumulatedToolCalls,
                      isToolCallsComplete: false,
                      toolResults: (msg.toolResults ?? {}) as Record<
                        string,
                        string
                      >,
                    }
                  : msg
              )
            );
          }

          if (chunk.role === "tool" && chunk.content && chunk.tool_call_id) {
            // Attach tool result to the assistant message instead of creating a separate message
            setMessages((prev) =>
              prev.map((msg) => {
                if (msg.id === assistantMessageId) {
                  const existingResults = (msg.toolResults ?? {}) as Record<
                    string,
                    string
                  >;
                  return {
                    ...msg,
                    toolResults: {
                      ...existingResults,
                      [chunk.tool_call_id as string]: chunk.content ?? "",
                    },
                    isToolCallsComplete: true,
                  };
                }
                return msg;
              })
            );

            toolCallsComplete = true;
          }

          if (chunk.content && chunk.role !== "tool") {
            // Mark tool calls as complete when assistant content starts streaming
            if (!toolCallsComplete && accumulatedToolCalls.length > 0) {
              toolCallsComplete = true;
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMessageId
                    ? { ...msg, isToolCallsComplete: true }
                    : msg
                )
              );
            }

            assistantContent += chunk.content;

            // Update message with content
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? {
                      ...msg,
                      text: assistantContent,
                      toolCalls: accumulatedToolCalls,
                      isToolCallsComplete: toolCallsComplete,
                      toolResults:
                        msg.toolResults || ({} as Record<string, string>),
                    }
                  : msg
              )
            );
          }
        }
      } catch (streamError) {
        console.error("Streaming error:", streamError);

        const response = await apiClient.chatCompletion(chatMessages, {
          stream: false,
        });
        assistantContent =
          response.choices[0]?.message?.content ||
          "抱歉，我遇到了一些問題。請稍後再試。";

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? { ...msg, text: assistantContent }
              : msg
          )
        );
      }
    } catch (error) {
      console.error("Error calling LyBot API:", error);

      const errorMessage: Message = {
        id: generateId(),
        text: "抱歉，我遇到了一些問題。請檢查網路連線或稍後再試。",
        sender: "assistant",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setIsStreaming(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-screen bg-background text-foreground">
      {/* Enhanced Modern Header */}
      <header className="border-b border-border/50 bg-background/95 backdrop-blur-md supports-[backdrop-filter]:bg-background/80 sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="relative group">
                <div className="flex items-center justify-center w-11 h-11 rounded-2xl bg-gradient-to-br from-violet-500 via-purple-500 to-fuchsia-600 shadow-lg group-hover:shadow-xl transition-all duration-300">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-emerald-400 rounded-full border-2 border-background shadow-sm">
                  <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse mx-auto mt-0.5" />
                </div>
              </div>
              <div className="flex flex-col">
                <h1 className="text-xl font-bold bg-gradient-to-r from-violet-600 via-purple-600 to-fuchsia-600 bg-clip-text text-transparent">
                  LyBot
                </h1>
                <p className="text-sm text-muted-foreground font-medium">
                  AI-Powered Legislative Assistant
                </p>
              </div>
              <div className="hidden md:flex">
                <div className="px-4 py-2 rounded-full bg-gradient-to-r from-emerald-100 via-teal-100 to-cyan-100 dark:from-emerald-900/40 dark:via-teal-900/40 dark:to-cyan-900/40 border border-emerald-300 dark:border-emerald-600 shadow-md">
                  <span className="text-sm font-bold text-emerald-800 dark:text-emerald-200 flex items-center gap-2">
                    <Zap className="w-4 h-4 text-emerald-700 dark:text-emerald-300" />
                    立法院專家
                  </span>
                </div>
              </div>
            </div>

            <Button
              variant="ghost"
              size="icon"
              onClick={toggleTheme}
              className="h-11 w-11 rounded-2xl hover:bg-muted/60 transition-all duration-200 group"
            >
              {isDark ? (
                <Sun className="h-5 w-5 text-muted-foreground group-hover:text-foreground transition-colors" />
              ) : (
                <Moon className="h-5 w-5 text-muted-foreground group-hover:text-foreground transition-colors" />
              )}
            </Button>
          </div>
        </div>
      </header>

      {/* Enhanced Messages Area */}
      <ScrollArea className="flex-1 bg-gradient-to-b from-background via-background to-muted/10">
        <div className="max-w-5xl mx-auto px-6 py-8">
          <div className="space-y-8">
            {messages
              .filter((msg) => msg.sender !== "tool")
              .map((message) => (
                <div
                  key={message.id}
                  className="animate-in fade-in-0 slide-in-from-bottom-2 duration-700"
                >
                  <div
                    className={`flex gap-5 ${
                      message.sender === "user"
                        ? "justify-end"
                        : "justify-start"
                    }`}
                  >
                    {message.sender === "assistant" && (
                      <div className="flex-shrink-0 w-10 h-10 rounded-2xl bg-gradient-to-br from-violet-200 via-purple-100 to-fuchsia-200 dark:from-violet-900/40 dark:via-purple-900/40 dark:to-fuchsia-900/40 border border-violet-300 dark:border-violet-600 flex items-center justify-center shadow-md">
                        <Sparkles className="w-5 h-5 text-white" />
                      </div>
                    )}

                    <div
                      className={`flex flex-col max-w-[80%] ${
                        message.sender === "user" ? "items-end" : "items-start"
                      }`}
                    >
                      <div
                        className={`relative group transition-all duration-300 overflow-x-auto ${
                          message.sender === "user"
                            ? "bg-gradient-to-br from-violet-500 via-purple-500 to-fuchsia-600 text-white px-6 py-4 rounded-3xl rounded-br-xl shadow-lg hover:shadow-xl hover:scale-[1.02]"
                            : "bg-card/80 backdrop-blur border border-border/60 px-6 py-5 rounded-3xl rounded-bl-xl shadow-sm hover:shadow-lg hover:bg-card/90 hover:border-border"
                        }`}
                      >
                        <div
                          className={`text-[15px] leading-relaxed break-words ${
                            message.sender === "assistant"
                              ? "text-card-foreground"
                              : "text-white"
                          }`}
                        >
                          {message.sender === "assistant" ? (
                            <div>
                              {/* Tool Calls Display */}
                              {message.toolCalls &&
                                message.toolCalls.length > 0 && (
                                  <ToolCallDisplay
                                    toolCalls={message.toolCalls}
                                    isComplete={
                                      message.isToolCallsComplete || false
                                    }
                                    toolResults={message.toolResults}
                                  />
                                )}

                              {/* Response Content */}
                              {message.text && (
                                <div className="prose prose-sm max-w-none dark:prose-invert prose-headings:text-card-foreground prose-p:text-card-foreground prose-strong:text-card-foreground prose-li:text-card-foreground prose-code:text-card-foreground prose-pre:bg-muted prose-pre:border prose-transcript">
                                  <ReactMarkdown
                                    remarkPlugins={[remarkGfm]}
                                    rehypePlugins={[
                                      rehypeRawPlugin,
                                      rehypeHighlightPlugin,
                                    ]}
                                    components={{
                                      pre: ({ children }) => (
                                        <pre className="bg-muted/50 border border-border rounded-lg p-4 overflow-x-auto">
                                          {children}
                                        </pre>
                                      ),
                                      code: ({ children, className }) => {
                                        const isInlineCode = !className;
                                        return isInlineCode ? (
                                          <code className="bg-muted/60 px-1.5 py-0.5 rounded text-sm font-mono">
                                            {children}
                                          </code>
                                        ) : (
                                          <code className={className}>
                                            {children}
                                          </code>
                                        );
                                      },
                                      p: ({ children }) => (
                                        <p className="my-4 leading-relaxed">
                                          {children}
                                        </p>
                                      ),
                                      strong: ({ children }) => (
                                        <strong
                                          className="font-bold text-lg block mt-6 mb-2 first:mt-0"
                                          style={{
                                            color: "hsl(var(--primary))",
                                          }}
                                        >
                                          {children}
                                        </strong>
                                      ),
                                      ul: ({ children }) => (
                                        <ul className="list-disc list-outside ml-6 space-y-2 my-4">
                                          {children}
                                        </ul>
                                      ),
                                      ol: ({ children }) => (
                                        <ol className="list-decimal list-outside ml-6 space-y-2 my-4">
                                          {children}
                                        </ol>
                                      ),
                                      li: ({ children }) => (
                                        <li className="leading-relaxed">
                                          {children}
                                        </li>
                                      ),
                                      blockquote: ({ children }) => (
                                        <blockquote className="border-l-4 border-primary/50 pl-4 my-4 italic bg-muted/30 py-2 pr-4 rounded-r-md">
                                          {children}
                                        </blockquote>
                                      ),
                                      table: ({ children }) => (
                                        <div className="table-container overflow-x-auto">
                                          <table className="w-full">
                                            {children}
                                          </table>
                                        </div>
                                      ),
                                      thead: ({ children }) => (
                                        <thead>{children}</thead>
                                      ),
                                      tbody: ({ children }) => (
                                        <tbody>{children}</tbody>
                                      ),
                                      tr: ({ children }) => <tr>{children}</tr>,
                                      th: ({ children }) => <th>{children}</th>,
                                      td: ({ children }) => <td>{children}</td>,
                                      a: ({ href, children }) => {
                                        if (href === "#disclaimer") {
                                          return (
                                            <DisclaimerDialog isDark={isDark} />
                                          );
                                        }
                                        return (
                                          <a
                                            href={href as string}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="text-violet-600 underline hover:text-violet-700"
                                          >
                                            {children}
                                          </a>
                                        );
                                      },
                                    }}
                                  >
                                    {transformPlanTags(message.text)}
                                  </ReactMarkdown>
                                </div>
                              )}
                            </div>
                          ) : (
                            <span className="whitespace-pre-wrap">
                              {message.text}
                            </span>
                          )}
                          {isStreaming && message.text === "" && (
                            <div className="flex items-center gap-1.5">
                              <div
                                className="w-2.5 h-2.5 rounded-full bg-current animate-pulse"
                                style={{ animationDelay: "0ms" }}
                              />
                              <div
                                className="w-2.5 h-2.5 rounded-full bg-current animate-pulse"
                                style={{ animationDelay: "200ms" }}
                              />
                              <div
                                className="w-2.5 h-2.5 rounded-full bg-current animate-pulse"
                                style={{ animationDelay: "400ms" }}
                              />
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 mt-3 px-3 text-xs text-muted-foreground/80">
                        <span className="font-medium">
                          {formatTimestamp(message.timestamp)}
                        </span>
                        {message.sender === "user" && message.status && (
                          <>
                            <span>•</span>
                            {message.status === "sending" ? (
                              <Circle className="w-3 h-3 animate-pulse text-amber-500" />
                            ) : message.status === "sent" ? (
                              <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                            ) : null}
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}

            {isLoading && !isStreaming && (
              <div className="flex gap-5 animate-in fade-in-0 duration-300">
                <div className="flex-shrink-0 w-10 h-10 rounded-2xl bg-gradient-to-br from-violet-200 via-purple-100 to-fuchsia-200 dark:from-violet-900/40 dark:via-purple-900/40 dark:to-fuchsia-900/40 border border-violet-300 dark:border-violet-600 flex items-center justify-center shadow-md">
                  <Sparkles className="w-4 h-4 text-white dark:text-white" />
                </div>

                <div className="bg-card/80 backdrop-blur border border-border/60 px-6 py-5 rounded-3xl rounded-bl-xl shadow-sm">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-2.5 h-2.5 rounded-full bg-violet-400 animate-pulse"
                      style={{ animationDelay: "0ms" }}
                    />
                    <div
                      className="w-2.5 h-2.5 rounded-full bg-purple-400 animate-pulse"
                      style={{ animationDelay: "200ms" }}
                    />
                    <div
                      className="w-2.5 h-2.5 rounded-full bg-fuchsia-400 animate-pulse"
                      style={{ animationDelay: "400ms" }}
                    />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>
      </ScrollArea>

      {/* Premium Input Area */}
      <div className="border-t border-border/50 bg-background/95 backdrop-blur-md supports-[backdrop-filter]:bg-background/80">
        <div className="max-w-5xl mx-auto px-6 py-5">
          <div className="bg-card/80 backdrop-blur border border-border/60 rounded-3xl px-5 py-4 shadow-lg transition-all duration-300 focus-within:shadow-xl focus-within:ring-2 focus-within:ring-violet-500/30 focus-within:border-violet-300 dark:focus-within:border-violet-600 group">
            <div className="flex items-end gap-4">
              <div className="flex-1">
                <Input
                  ref={inputRef}
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="詢問關於立法院的任何問題..."
                  className="min-h-[44px] px-0 py-2 text-[16px] bg-transparent border-0 shadow-none focus-visible:ring-0 focus-visible:ring-offset-0 placeholder:text-muted-foreground/60 resize-none"
                  disabled={isLoading || isStreaming}
                />
              </div>

              <Button
                onClick={handleSendMessage}
                disabled={isLoading || isStreaming || inputValue.trim() === ""}
                className="bg-gradient-to-r from-violet-500 via-purple-500 to-fuchsia-600 hover:from-violet-600 hover:via-purple-600 hover:to-fuchsia-700 text-white border-0 h-11 w-11 rounded-2xl transition-all duration-300 shadow-lg hover:shadow-xl hover:scale-110 disabled:opacity-50 disabled:hover:scale-100 disabled:cursor-not-allowed group"
              >
                <Send className="w-4 h-4 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform duration-200" />
              </Button>
            </div>
          </div>

          <div className="flex items-center justify-between px-5 pt-4 text-xs text-muted-foreground/70">
            <div className="flex items-center gap-6">
              <span className="flex items-center gap-1.5 font-medium">
                <kbd className="px-2 py-1 text-xs bg-muted/80 rounded-lg border border-border/60 shadow-sm font-mono">
                  Enter
                </kbd>
                傳送
              </span>
              <span className="flex items-center gap-1.5 font-medium">
                <kbd className="px-2 py-1 text-xs bg-muted/80 rounded-lg border border-border/60 shadow-sm font-mono">
                  Shift
                </kbd>
                <kbd className="px-2 py-1 text-xs bg-muted/80 rounded-lg border border-border/60 shadow-sm font-mono">
                  Enter
                </kbd>
                換行
              </span>
            </div>
            <span className="text-xs font-medium bg-gradient-to-r from-violet-600 to-purple-600 bg-clip-text text-transparent">
              Built with ❤️ by{" "}
              <a
                href="https://codeer.ai"
                target="_blank"
                rel="noopener noreferrer"
                className="text-violet-600 hover:text-violet-700 transition-colors"
              >
                Codeer.ai
              </a>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
