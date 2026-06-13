import { cn } from "@arata-ai/applications-core/libs/utils";
import { Icon, IconName } from "@arata-ai/applications-core/ui/components/icon";
import { P } from "@arata-ai/applications-core/ui/components/typography";
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@arata-ai/applications-core/ui/primitives/avatar";
import { Button } from "@arata-ai/applications-core/ui/primitives/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@arata-ai/applications-core/ui/primitives/popover";
import { useLogout } from "@/hooks/use-logout";
import { useUser } from "@/hooks/use-user";

interface UserProfileProps {
  isExpanded?: boolean;
}

export function UserProfile({ isExpanded = true }: UserProfileProps) {
  const { user } = useUser();
  const { logout } = useLogout();
  if (!user) {
    return null;
  }
  return (
    <div className={cn("flex items-center gap-2")}>
      <Popover>
        <PopoverTrigger
          asChild
          className={cn(
            "w-full",
            isExpanded ? "justify-start" : "justify-center",
          )}
        >
          <Button
            variant="ghost" colourTheme="default"
            size="lg"
            className={isExpanded ? "w-full px-3" : "w-full mx-auto"}
          >
            <Avatar className="w-8 h-8">
              <AvatarImage src={user.picture} alt={user.name ?? "User"} />
              <AvatarFallback>{user.name?.charAt(0) ?? "U"}</AvatarFallback>
            </Avatar>
            {isExpanded && <P className="text-base">{user.name ?? "User"}</P>}
          </Button>
        </PopoverTrigger>
        <PopoverContent
          className="w-(--radix-popover-trigger-width) p-2 min-w-52 flex flex-col gap-1"
          align="start"
          sideOffset={4}
        >
          <Button
            variant="ghost" colourTheme="default"
            size="md"
            className="w-full justify-start text-red-500"
            onClick={() => {
              logout();
            }}
          >
            <Icon name={IconName.LogOut} size={20} />
            Logout
          </Button>
        </PopoverContent>
      </Popover>
    </div>
  );
}
