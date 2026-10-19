-- همه‌ی آگهی‌های تلگرامیِ یک کانال را از Redis سایت (back-redis) پاک می‌کند.
-- ARGV[1] = یوزرنیم کانال (بدون @، بزرگ/کوچکی حروف مهم نیست)
-- اجرا:  docker exec <redis> redis-cli --eval /tmp/delete_site_channel.lua , akhbar1khatii
local wanted = string.lower(ARGV[1])
local idx = {
  'tg:idx:all', 'tg:idx:priced', 'tg:idx:unpriced', 'tg:idx:misc', 'tg:idx:buyer',
  'tg:idx:deal:urgent', 'tg:idx:deal:mofat', 'tg:idx:deal:goodprice', 'tg:idx:deal:close',
  'tg:idx:deal:floor', 'tg:idx:deal:agreed', 'tg:idx:deal:negotiable'
}
local removed = 0
local names = {}
local cursor = '0'
repeat
  local res = redis.call('SCAN', cursor, 'MATCH', 'tg:showroom:*:ads', 'COUNT', 1000)
  cursor = res[1]
  for _, setKey in ipairs(res[2]) do
    local name = string.sub(setKey, 13, -5)  -- tg:showroom:{name}:ads
    if string.lower(name) == wanted then
      table.insert(names, name)
      for _, id in ipairs(redis.call('SMEMBERS', setKey)) do
        local adKey = 'tg:ad:' .. id
        local json = redis.call('GET', adKey)
        if json then
          local ok, ad = pcall(cjson.decode, json)
          if ok and type(ad) == 'table' then
            local src = ad['TelegramSourceId'] or ad['telegramSourceId']
            if type(src) == 'string' and src ~= '' then redis.call('DEL', 'tg:src:' .. src) end
            local vk = ad['VehicleKey'] or ad['vehicleKey']
            if type(vk) == 'string' and vk ~= '' then redis.call('ZREM', 'tg:idx:vehicle:' .. vk, id) end
          end
        end
        for _, k in ipairs(idx) do redis.call('ZREM', k, id) end
        redis.call('DEL', adKey)
        removed = removed + 1
      end
      redis.call('DEL', setKey)
      redis.call('DEL', 'tg:showroom:' .. name .. ':name')
      redis.call('ZREM', 'tg:showrooms:active', name)
    end
  end
until cursor == '0'
return {removed, table.concat(names, ',')}
