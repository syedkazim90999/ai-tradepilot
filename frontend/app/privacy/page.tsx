import { PublicLayout } from "@/components/layout/public-layout";

export default function PrivacyPage() {
  return (
    <PublicLayout title="Privacy Policy" intro="Last updated: November 2026.">
      <h2 className="text-xl font-semibold text-white">1. Data we collect</h2>
      <p>We collect your email address, name (if provided), account settings, bot configuration, trade and signal history, notifications, and technical data such as IP address and session information needed for security.</p>
      <h2 className="text-xl font-semibold text-white">2. Binance API keys</h2>
      <p>API keys and secrets you connect are encrypted before storage. Only the last 4 characters of a key are ever displayed. We never store a key in plain text, never display a secret, and never request withdrawal permission — keys with withdrawal permission are refused.</p>
      <h2 className="text-xl font-semibold text-white">3. How we use data</h2>
      <p>Your data is used to operate the service: authentication, scanning, signal generation, trade execution, notifications and support. We do not sell your personal data.</p>
      <h2 className="text-xl font-semibold text-white">4. Security</h2>
      <p>Passwords are hashed with Argon2id. Sessions can be reviewed and revoked from Settings. Admin actions are recorded in an audit log. No system is perfectly secure; report suspected breaches to support promptly.</p>
      <h2 className="text-xl font-semibold text-white">5. Retention and deletion</h2>
      <p>We keep account data while your account is active. You can disconnect Binance keys at any time. To request deletion of your account and personal data, contact support from your registered email address.</p>
      <h2 className="text-xl font-semibold text-white">6. Cookies and local storage</h2>
      <p>The web app stores your authentication token in your browser&rsquo;s local storage so you stay signed in. Clearing it signs you out. We do not use third-party advertising trackers.</p>
      <h2 className="text-xl font-semibold text-white">7. Contact</h2>
      <p>Questions about this policy can be sent via the <a className="text-blue-400 underline" href="/contact">contact page</a>.</p>
    </PublicLayout>
  );
}
