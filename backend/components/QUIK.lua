-- executive_script.lua
is_run = true
local is_processing = false

-- Simple counter for TRANS_ID
local trans_id_counter = 1000

-- FUNCTION: Logging (file only)
function log_message(msg)
    local log_file = io.open("C:/QUIK_DATA/script_log.txt", "a")
    if log_file then
        log_file:write(os.date("%Y-%m-%d %H:%M:%S") .. " - " .. msg .. "\n")
        log_file:close()
    end
end

-- FUNCTION: Get ALL orders (including non-activated)
function get_all_orders_for_ticker(ticker)
    log_message("Searching for ALL orders: " .. ticker)

    local orders_found = {}
    local row_count = getNumberOf("orders") or 0
    log_message("Total orders in table: " .. row_count)

    for i = 0, row_count - 1 do
        local order = getItem("orders", i)
        if order and order.sec_code == ticker then
            local status = tostring(order.status or "0")
            local balance = tonumber(order.balance or 0) or 0
            local order_num = tostring(order.order_num or "")
            local price = tostring(order.price or "nil")
            local trans_id = tostring(order.trans_id or "nil")

            log_message("Found order " .. i .. ":")
            log_message("  ORDER_NUM: " .. order_num)
            log_message("  TRANS_ID: " .. trans_id)
            log_message("  STATUS: " .. status .. " (0=NEW,1=ACTIVE,2=FILLED,3=CANCELLED)")
            log_message("  BALANCE: " .. tostring(balance))
            log_message("  PRICE: " .. price)

            if order_num ~= "" and order_num ~= "0" then
                table.insert(orders_found, {
                    order_num = order_num,
                    trans_id = trans_id,
                    status = status,
                    balance = balance,
                    price = price
                })
            end
        end
    end

    return orders_found
end

-- FUNCTION: Cancel order - SIMPLE AND RELIABLE
function kill_order_simple(ticker)
    if not ticker or ticker == "" then
        log_message("CANCEL ERROR: No ticker specified")
        return false
    end

    log_message("=== CANCEL ORDER FOR: " .. ticker .. " ===")

    -- 1. Get all orders for this ticker
    local orders = get_all_orders_for_ticker(ticker)

    if #orders == 0 then
        log_message("ERROR: No orders found for " .. ticker)
        return false
    end

    -- 2. Try to cancel each found order
    local any_success = false

    for _, order in ipairs(orders) do
        log_message("Trying to cancel order: " .. order.order_num ..
                   " (status=" .. order.status .. ", balance=" .. order.balance .. ")")

        -- Создаем новую транзакцию для каждой попытки
        trans_id_counter = trans_id_counter + 1

        -- МЕТОД 1: Используем ORDER_KEY (наиболее надежный для фьючерсов)
        local transaction1 = {
            ["ACTION"] = "KILL_ORDER",
            ["CLASSCODE"] = "SPBFUT",
            ["SECCODE"] = ticker,
            ["ORDER_KEY"] = order.order_num,
            ["ACCOUNT"] = "L01+00000F00",
            ["CLIENT_CODE"] = "QLUA_MKT",
            ["TRANS_ID"] = tostring(trans_id_counter)
        }

        log_message("Method 1: Using ORDER_KEY=" .. order.order_num)
        local result1 = sendTransaction(transaction1)

        if result1 == "" then
            log_message("SUCCESS: Order " .. order.order_num .. " canceled!")
            any_success = true
        else
            log_message("Method 1 failed: " .. result1)

            -- МЕТОД 2: Пробуем ORDER_NUM
            trans_id_counter = trans_id_counter + 1

            local transaction2 = {
                ["ACTION"] = "KILL_ORDER",
                ["CLASSCODE"] = "SPBFUT",
                ["SECCODE"] = ticker,
                ["ORDER_NUM"] = order.order_num,
                ["ACCOUNT"] = "L01+00000F00",
                ["CLIENT_CODE"] = "QLUA_MKT",
                ["TRANS_ID"] = tostring(trans_id_counter)
            }

            log_message("Method 2: Using ORDER_NUM=" .. order.order_num)
            local result2 = sendTransaction(transaction2)

            if result2 == "" then
                log_message("SUCCESS: Order " .. order.order_num .. " canceled!")
                any_success = true
            else
                log_message("Method 2 failed: " .. result2)

                -- МЕТОД 3: Пробуем без TRANS_ID
                local transaction3 = {
                    ["ACTION"] = "KILL_ORDER",
                    ["CLASSCODE"] = "SPBFUT",
                    ["SECCODE"] = ticker,
                    ["ORDER_KEY"] = order.order_num,
                    ["ACCOUNT"] = "L01+00000F00",
                    ["CLIENT_CODE"] = "QLUA_MKT"
                }

                log_message("Method 3: Without TRANS_ID")
                local result3 = sendTransaction(transaction3)

                if result3 == "" then
                    log_message("SUCCESS: Order " .. order.order_num .. " canceled!")
                    any_success = true
                else
                    log_message("Method 3 failed: " .. result3)
                end
            end
        end

        -- Пауза между попытками
        if not any_success then
            local wait_start = os.clock()
            while os.clock() - wait_start < 0.5 do end
        end
    end

    if any_success then
        log_message("=== CANCEL SUCCESSFUL for " .. ticker .. " ===")
        return true
    else
        log_message("=== ALL CANCEL ATTEMPTS FAILED for " .. ticker .. " ===")
        return false
    end
end

-- FUNCTION: Process received orders (без записи в ORDER_KEY.txt)
function OnOrder(order)
    log_message("=== ONORDER ===")

    -- Log status
    if order.status then
        local status_names = {
            ["0"] = "NEW",
            ["1"] = "ACTIVE",
            ["2"] = "FILLED",
            ["3"] = "CANCELLED"
        }
        local status_name = status_names[tostring(order.status)] or "UNKNOWN"
        log_message("Status: " .. order.status .. " (" .. status_name .. ")")
    end

    log_message("=== ONORDER END ===")
end

-- FUNCTION: Manual test function
function test_cancel()
    log_message("=== MANUAL CANCEL TEST ===")

    local ticker = "GLDRUBF"  -- Измените на нужный тикер

    local result = kill_order_simple(ticker)

    if result then
        log_message("TEST: Cancel successful!")
    else
        log_message("TEST: Cancel failed!")
    end

    log_message("=== TEST END ===")
end

-- MAIN FUNCTION
function main()
    local price_file = "C:/QUIK_DATA/CREATE_PRICE.txt"
    local order_file = "C:/QUIK_DATA/CREATE_ORDER.txt"
    local status_file = "C:/QUIK_DATA/KIL_ORDER.txt"

    local instruments = {
        {class = "SPBFUT", ticker = "GLDRUBF", code = "GLDRUBF"},
        {class = "SPBFUT", ticker = "IMOEXF", code = "IMOEXF"},
        {class = "SPBFUT", ticker = "VBH6", code = "VTBR-3.26"},
        {class = "SPBFUT", ticker = "NAH6", code = "NASD-3.26"},
        {class = "SPBFUT", ticker = "YDH6", code = "YDEX-3.26"},
        {class = "SPBFUT", ticker = "SRH6", code = "SBRF-3.26"},
        {class = "SPBFUT", ticker = "GZH6", code = "GAZR-3.26"},
        {class = "SPBFUT", ticker = "BRH6", code = "BR-3.26"}
    }

    log_message("Script started")

    while is_run do
        -- 1. WRITE PRICES TO price.txt
        local price_strings = {}
        for i, instr in ipairs(instruments) do
            local price_data = getParamEx(instr.class, instr.ticker, "LAST")
            if price_data and price_data.param_value and price_data.param_value ~= "" then
                table.insert(price_strings, instr.code .. ":" .. price_data.param_value)
            end
        end

        local new_price_line = table.concat(price_strings, "; ")

        local price_file_write = io.open(price_file, "w")
        if price_file_write then
            price_file_write:write(new_price_line .. "\n")
            price_file_write:close()
        end

        -- 2. PROCESS NEW ORDERS FROM order.txt
        if not is_processing then
            is_processing = true

            local order_file_read = io.open(order_file, "r")
            if order_file_read then
                local lines = {}
                local has_deals = false

                for line in order_file_read:lines() do
                    table.insert(lines, line)
                    if string.sub(line, 1, 5) == "DEAL:" then
                        has_deals = true
                    end
                end
                order_file_read:close()

                if has_deals then
                    log_message("Found deals to process")
                    local updated_lines = {}

                    for i, line in ipairs(lines) do
                        if string.sub(line, 1, 5) == "DEAL:" then
                            local deal_data = string.sub(line, 6)

                            local ticker, operation, order_type, quantity, price =
                                string.match(deal_data, "(.+)/(.)/(.)/(%d+)/(.+)")

                            if ticker and operation and order_type and quantity and price then
                                ticker = string.gsub(ticker, "%s+", "")
                                operation = string.gsub(operation, "%s+", "")
                                order_type = string.gsub(order_type, "%s+", "")
                                quantity = string.gsub(quantity, "%s+", "")
                                price = string.gsub(price, "%s+", "")

                                local transaction_price = ""
                                if order_type == "L" then
                                    transaction_price = price
                                    log_message("Limit order: " .. ticker .. " " .. operation .. " " .. quantity .. " @ " .. price)
                                elseif order_type == "M" then
                                    transaction_price = "0"
                                    log_message("Market order: " .. ticker .. " " .. operation .. " " .. quantity)
                                end

                                trans_id_counter = trans_id_counter + 1
                                local my_trans_id = tostring(trans_id_counter)

                                local transaction = {
                                    ["ACTION"] = "NEW_ORDER",
                                    ["CLASSCODE"] = "SPBFUT",
                                    ["SECCODE"] = ticker,
                                    ["OPERATION"] = operation,
                                    ["QUANTITY"] = tostring(quantity),
                                    ["PRICE"] = transaction_price,
                                    ["ACCOUNT"] = "L01+00000F00",
                                    ["TYPE"] = order_type,
                                    ["CLIENT_CODE"] = "QLUA_MKT",
                                    ["TRANS_ID"] = my_trans_id
                                }

                                local result = sendTransaction(transaction)

                                if result == "" then
                                    log_message("Order sent - TRANS_ID: " .. my_trans_id)
                                else
                                    table.insert(updated_lines, line)
                                    log_message("Send error: " .. result)
                                end
                            else
                                table.insert(updated_lines, line)
                                log_message("Format error: " .. line)
                            end
                        else
                            table.insert(updated_lines, line)
                        end
                    end

                    local order_file_write = io.open(order_file, "w")
                    if order_file_write then
                        for _, line in ipairs(updated_lines) do
                            order_file_write:write(line .. "\n")
                        end
                        order_file_write:close()
                        log_message("order.txt updated")
                    end
                end
            end

            is_processing = false
        end

        -- 3. MONITOR STATUS_ORDER.txt FOR CANCELLATION
        local status_file_read = io.open(status_file, "r")
        if status_file_read then
            local status_lines = {}
            local lines_to_keep = {}
            local file_has_content = false

            for line in status_file_read:lines() do
                file_has_content = true
                table.insert(status_lines, line)

                -- Format: "TICKER" (только тикер, без двоеточий и ключей)
                local ticker = string.match(line, "([^%s]+)")
                if ticker then
                    ticker = string.gsub(ticker, "%s+", "")

                    if ticker ~= "" then
                        log_message("=== PROCESSING CANCEL COMMAND for: " .. ticker .. " ===")

                        -- CANCEL ALL orders for this ticker
                        local cancel_result = kill_order_simple(ticker)

                        if cancel_result then
                            log_message("Cancel successful for " .. ticker)
                            -- Line processed, don't add back
                        else
                            table.insert(lines_to_keep, line)
                            log_message("Cancel failed for " .. ticker .. ", keeping line")
                        end
                    else
                        table.insert(lines_to_keep, line)
                    end
                else
                    table.insert(lines_to_keep, line)
                end
            end
            status_file_read:close()

            -- Rewrite file if needed
            if #lines_to_keep > 0 then
                local status_file_write = io.open(status_file, "w")
                if status_file_write then
                    for _, line in ipairs(lines_to_keep) do
                        status_file_write:write(line .. "\n")
                    end
                    status_file_write:close()
                end
            elseif file_has_content then
                -- Clear file if all lines processed
                local status_file_write = io.open(status_file, "w")
                if status_file_write then
                    status_file_write:write("")
                    status_file_write:close()
                end
            end
        end

        -- Delay
        local wait_start = os.clock()
        while os.clock() - wait_start < 1.0 and is_run do end
    end
end

-- FUNCTION: Stop script
function OnStop()
    is_run = false
    log_message("Script stopped")
end