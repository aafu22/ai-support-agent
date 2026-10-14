export type Role = "owner" | "agent";
export interface User { id: string; email: string; full_name: string; role: Role; is_active: boolean }
export interface Org { id: string; name: string; public_key: string; settings: { bot_name?: string; greeting?: string; support_email?: string | null } }
export interface Me { user: User; organization: Org }
export interface Doc { id: string; title: string; source_type: string; file_type: string | null; file_size: number; status: "processing" | "ready" | "failed"; error_message: string | null; chunk_count: number; created_at: string }
export interface Source { id: number; document_id: string; title: string; page: number | null; snippet: string }
export interface Msg { id: string; role: "customer" | "assistant" | "human_agent" | "system"; content: string; sources: Source[] | null; created_at: string; intent?: string | null; confidence?: number | null; is_unanswered?: boolean }
export interface Conversation { id: string; status: "ai_active" | "escalated" | "resolved"; customer_name: string | null; customer_email: string | null; summary: string | null; last_message_at: string; created_at: string; preview: string | null }
export interface ConversationDetail extends Conversation { messages: Msg[]; ticket_id: string | null }
export interface Ticket { id: string; conversation_id: string; status: "open" | "in_progress" | "resolved"; priority: "low" | "medium" | "high"; escalation_reason: string; summary: string | null; customer_email: string | null; assigned_to: string | null; created_at: string; resolved_at: string | null }
export interface Summary { total_conversations: number; total_messages: number; resolved_conversations: number; escalated_conversations: number; open_tickets: number; unanswered_questions: number; feedback_positive: number; feedback_negative: number; conversations_by_day: { date: string; count: number }[] }
export interface Unanswered { question: string; conversation_id: string; created_at: string }
export interface ChatReply { conversation_id: string; message_id: string | null; reply: string; sources: Source[]; status: string; ai_replied: boolean }
export interface PublicConversation { status: string; messages: Msg[] }
