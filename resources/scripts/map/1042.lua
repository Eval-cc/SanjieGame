-- 生成NPC
function OnCreate(EFun)
--     EFun.add_npc(1,861, 120, 0)
    EFun.add_npc(2,900, 400, 0)
    EFun.add_npc(3,940, 550, 0)
    EFun.add_npc(4,166, 1124, 0)
    EFun.add_npc(5,504, 726, 0)
    EFun.add_npc(6,1045, 769, 0)
    EFun.add_npc(6,900, 350, 0)
end

function OnTimer(EFun, id, e)
    -- 5分钟输出一次
    if e % 300 == 0 then
        EFun.log("场景ID = " .. id)
    end
end