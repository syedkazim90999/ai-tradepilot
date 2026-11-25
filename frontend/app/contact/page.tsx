"use client";
import { useState } from "react";
import { Mail } from "lucide-react";
import { PublicLayout } from "@/components/layout/public-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";

/**
 * Contact form. Submits to POST /api/v1/contact, which stores the message
 * for the admin team. Never send passwords or API secrets here.
 */
import { userApi } from "@/lib/api";
export default function ContactPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      await userApi.contact(name, email, message);
      setSent(true);
    } catch {
      setError("Could not send your message. Please try again later.");
    } finally { setBusy(false); }
  };

  return (
    <PublicLayout title="Contact us" intro="Questions, feedback or a bug report — we'd like to hear it.">
      <Alert title="How this form works">
        Your message is stored on our server for the support team. Nothing is sent to your email app.
      </Alert>
      {sent && <Alert variant="success" title="Message sent">Thanks — your message has been received. We will reply to the email address you gave.</Alert>}
      {error && <Alert variant="error">{error}</Alert>}
      <Card>
        <CardHeader><CardTitle>Send a message</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4">
            <div className="space-y-2"><Label htmlFor="name">Name</Label><Input id="name" value={name} onChange={(e) => setName(e.target.value)} required /></div>
            <div className="space-y-2"><Label htmlFor="email">Email</Label><Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></div>
            <div className="space-y-2"><Label htmlFor="message">Message</Label>
              <textarea id="message" value={message} onChange={(e) => setMessage(e.target.value)} required rows={6}
                className="flex w-full rounded-md border border-border bg-[#0D1424] px-3 py-2 text-sm text-white placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent" />
            </div>
            <Button type="submit" disabled={busy}><Mail className="h-4 w-4" /> {busy ? "Sending…" : sent ? "Send another message" : "Send message"}</Button>
          </form>
        </CardContent>
      </Card>
      <p className="text-sm text-muted">For account or trading issues, include your registered email address (never your API secret or password) so support can find your account.</p>
    </PublicLayout>
  );
}
