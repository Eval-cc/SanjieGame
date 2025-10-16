function add_money(params)
    bag = params[0]
    if(bag.money < 2100000000)
    then
        bag.money = bag.money + params[1]
        return true
    else
        return false
    end
end


function add_point(params)
    bag = params[0]
    if(bag.money < 2100000000)
    then
        bag.point = bag.point + params[1]
        return true
    else
        return false
    end
end
