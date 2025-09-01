import { AgentProvider } from "@/app/context/AgentsContext";

export default function AgentsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AgentProvider>{children}</AgentProvider>;
}