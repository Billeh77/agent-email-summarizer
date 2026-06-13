# Email Summarizer

Receives emails, generates AI summaries of the email body and attachments, persists summaries to the database, and replies to the sender with the summary

## Running locally

To run the workflow locally, you need to have a Temporal server running, as well as the database, etc.
To setup your local dev environment, clone `https://github.com/Arata-AI/tools/` and follow the [README in local-stack](https://github.com/Arata-AI/tools/tree/main/local-stack)
This sets up your local dev environment with the necessary infrastructure, including Temporal.
You can access the temporal web UI at `http://localhost:8233` to see your workflows running.

The example workflows can be run via the `run_locally.sh` script. For example:

```bash
./run_locally.sh summarize_email-worker
```

By default, `run_locally.sh` loads `dev` environment variables. To run against another environment, pass `dev`, `staging`, or `prod` before or after the workflow command:

```bash
./run_locally.sh staging <workflow>-worker
./run_locally.sh <workflow>-worker staging
```
will start one of the workers for the summarize_email workflow.
Once it is running, you can trigger the workflow execution from another terminal window with the following command:

```bash
./run_locally.sh summarize_email-runner
```

You should see the workflow execution in the Temporal web UI.

Remember that Temporal workflows are regular python code, wrapped with a decorator.
This means you can test them like regular python code, without needing to run a Temporal server, by calling the workflow function directly.
This is useful for quick iteration and debugging of your workflow logic.

## Things to remember when building your workflow

### Add activities and workflows to your worker

Each worker explicitly lists the workflows and activities it can run in a block like shown here.

```python
worker = Worker(
    client,
    task_queue="some-queue-tq",
    workflows=[MyWorkflow, MyOtherWorkflow],
    activities=[
        first_activity, second_activity, third_activity
    ],
)
```

When editing your workflow, make sure to update the worker.

### Best practice: always create a pydantic object for workflow and activity inputs/outputs

While your workflow and activity functions can technically take any serializable input, using pydantic objects has a
few advantages:
- better documentation of what the inputs and outputs are
- better validation of inputs and outputs (e.g. making sure required fields are present, or
  that fields are of the correct type)
- easier to maintain backwards compatibility when changing the workflow or activity inputs/outputs (e.g. by adding
  new optional fields to the pydantic model)

### Interactions between workflows

If you asked for multiple workflows to be created, you probably need them to interact with each other at some point (e.g. one workflow calls another workflow, or one workflow calls an activity that is implemented in another workflow).
By default, the project structure has the workflows isolated from each other (so that the resulting docker images are as small as possible).
To enable interactions between the workflows, you need to do a few things:

1. update the `[tool.uv.sources]` section of the `pyproject.toml` file to include the workflow you want to import from.
   If workflow A wants to import from workflow B, workflow A's `pyproject.toml` file needs to include workflow B.
   It is not required for B to include A.
2. uncomment lines in your Dockerfile that copy the workflow you want to import from (notice this needs to be done once for the builder and once for the final image)
   Again, this only needs to be done for the importing workflow, not the one being imported from.

## App (Frontend)

Full-stack React application using TanStack Start, tRPC, Shadcn UI, and Tailwind CSS v4.

### Quick Start

```bash
pnpm install
pnpm dev       # http://localhost:5174
pnpm build     # Production build
pnpm start     # Preview production build
```

### Tech Stack

| Tool | Purpose |
|------|---------|
| TanStack Start | SSR framework |
| TanStack Router | File-based routing |
| TanStack Query | Data fetching & caching |
| tRPC | Type-safe APIs |
| Shadcn UI | Component library |
| Tailwind CSS v4 | Styling |
| Biome | Linting & formatting |
| Nitro | Deployment engine |
| Auth0 | Authentication |

### Project Structure

```text
src/
├── routes/              # File-based routes
├── integrations/
│   ├── trpc/            # tRPC setup and routers
│   └── tanstack-query/  # Query client config
├── auth/                # Auth0 integration
├── components/          # App components
├── env.ts               # Type-safe env vars (T3 Env)
└── styles.css           # Tailwind imports
```

### UI Components

- **Shadcn primitives**: `packages/core/ui/components/primitives/` → import from `@arata-ai/applications-core/ui/primitives/*`
- **Custom components**: `packages/core/ui/components/` → import from `@arata-ai/applications-core/ui/components/*`

```bash
# Add a Shadcn component
cd packages/core && pnpm dlx shadcn@latest add <component>
```

### Useful Commands

```bash
pnpm lint      # Check for issues
pnpm format    # Fix formatting
pnpm check     # Lint + format
pnpm test      # Run tests (Vitest)
```

Tailwind CSS v4 imports:

```css
/* src/styles.css */
@import "tailwindcss";
@import "@arata-ai/applications-core/tailwind-config";
@import "@arata-ai/applications-core/ui/globals.css";
```

### Deployment (Azure Static Web Apps)

```bash
NITRO_PRESET=azure pnpm build
```

Configure environment variables in Azure Portal → Static Web App → Configuration → Application settings.
