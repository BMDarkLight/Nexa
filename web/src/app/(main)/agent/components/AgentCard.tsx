import React from "react";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge"
import { Bot, EllipsisVertical, Plus, Trash2 } from "lucide-react";
import {Tooltip , TooltipContent , TooltipProvider , TooltipTrigger} from "@/components/ui/tooltip";
import DeleteAgent from "./DeleteAgent";
import Link from "next/link";
const tooltipIcon = [{
      name:"Figma" , src: "/Squad/image/figma.png"
} , { name:"Google Drive" , src:"/Squad/image/goole-drive.png"} , {name:"Notion" , src:"/Squad/image/notion.png"} , {name:"Temple" , src:"/Squad/image/temple.png"}]
export default function AgentCard(){
      return(
            <>
             <div className="flex flex-col gap-5 lg:px-10">
                  <div className="flex justify-between mt-4 md:mt-0 items-center">
                        <h2 className="text-xl font-medium">لیست ایجنت ‌ها</h2>
                        <Link href="/agent/new-agent"><Button className="cursor-pointer text-xs md:text-sm">ایجنت جدید <Plus /></Button></Link>
                  </div>
                  <div className="flex justify-between flex-wrap gap-5 md:grid lg:grid-cols-3 md:grid-cols-2 lg:gap-2">
                        <Card className="w-full text-center">
                 <div className="">
                 <div>
                   <CardHeader className="flex flex-col items-center relative">
                       <DeleteAgent />
                        <div className="w-[72px] h-[72px] rounded-full flex justify-center items-center bg-card-foreground text-primary-foreground my-2">
                              <Bot  size={50}/>
                        </div>
                     <CardTitle className="sm:text-base font-medium text-sm">نام ایجنت</CardTitle>
                </CardHeader>
            <CardContent className="my-2">
                 <div className="flex justify-between text-xs md:text-sm mb-3">
                  <p className="">وضعیت</p>
                  <Badge className="bg-[#0596691A] text-[#047857]">فعال</Badge>
                 </div>
                 <div className="flex justify-between text-xs md:text-sm">
                  <p>اتصالات</p>
                  <div>
                       <TooltipProvider>
                        <div className="flex flex-row-reverse -space-x-1">
                              {tooltipIcon.map((item , index)=>(
                                    <Tooltip key={index}>
                                          <TooltipTrigger asChild>
                                                <div className="w-5 h-5 rounded-full overflow-hidden cursor-pointer transition-transform hover:scale-110 border-1">
                                                      <img src={item.src} alt={item.name} className="object-cover w-full h-full"/>
                                                </div>
                                          </TooltipTrigger>
                                          <TooltipContent>
                                                <p>{item.name}</p>
                                          </TooltipContent>
                                    </Tooltip>
                              ))}
                        </div>
                       </TooltipProvider>
                  </div>
                 </div>
           </CardContent>
           <div>
            <CardFooter className="w-full">
             <Button className="cursor-pointer bg-transparent border-1 text-black w-full hover:text-secondary mt-2">ویرایش</Button>
       </CardFooter>
           </div>
                 </div>
                 </div>
            </Card>
            
                  </div>
               </div>
            
            </>
      )
}