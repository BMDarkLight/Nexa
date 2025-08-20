"use client"

import * as React from "react"
import {
  AudioWaveform,
  BookOpen,
  Bot,
  BotIcon,
  Command,
  Frame,
  GalleryVerticalEnd,
  LogOut,
  Map,
  MessageSquare,
  PieChart,
  Plus,
  Settings,
  Settings2,
  SquareTerminal,
  Unplug,
} from "lucide-react"

import { NavMain } from "@/components/nav-main"
import { NavProjects } from "@/components/nav-projects"
import { NavUser } from "@/components/nav-user"
import { TeamSwitcher } from "@/components/team-switcher"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarRail,
} from "@/components/ui/sidebar"
import { Button } from "./ui/button"

// This is sample data.
const data = {
  user: {
    name: "",
    email: "m@example.com",
    avatar: "/avatars/shadcn.jpg",
  },
  teams: [
    {
      name: "نکسا",
      logo: GalleryVerticalEnd,
      plan: "ورژن 1.0.0",
    },
  ],
  navMain: [
    {
      title: "گفتگوها",
      url: "#",
      icon: MessageSquare,
      isActive: true,
      items: [
        {
          title: "شروع مکالمه",
          url: "#",
        },
        {
          title: "سلام وقت بخیر",
          url: "#",
        },
        {
          title: "تحلیل دیتای مالی",
          url: "#",
        },
      ],
    },
  ],
  projects: [
    {
      name: "ایجنت ها",
      url: "/agent",
      icon: BotIcon,
      type : "link" , 
      hasChild : true ,
    },
    {
      name: "اتصالات و داده ها",
      url: "/connector",
      icon: Unplug,
       type : "link" , 
        hasChild : false
    },
    {
      name: "تنظیمات و اعتبار",
      url: "",
      icon: Settings,
       type : "alert"
    },
     {
      name: "خروج از حساب",
      url: "",
      icon: LogOut,
      color : "text-red-600 " , 
       type : "action"
    },
  ],
}

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <TeamSwitcher teams={data.teams} />
        <div className="">
          <Button className="w-full border-1 bg-transparent text-primary cursor-pointer hover:bg-primary hover:text-secondary">گفتگو جدید <Plus/></Button>
        </div>
      </SidebarHeader>
      <SidebarContent className="flex flex-col justify-between">
          <NavMain items={data.navMain} />
          <NavProjects projects={data.projects} />
      </SidebarContent>
      <SidebarFooter>
        <NavUser user={data.user} />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
