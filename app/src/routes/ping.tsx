import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/ping")({
  component: () => {
    return <div>OK</div>;
  },
  loader: async () => {
    return "OK";
  },
});
