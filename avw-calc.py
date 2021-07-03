import rpc
import argparse
from gooey import Gooey
import sys

GUI_mode = True

#for fancier formatting and so total_steps can be more easily changed
#also works more nicely with a regex for Gooey's progress bar
def progress(step:int) -> str:
    total_steps = 5
    return (" | " + "step " + str(step) + "/" + str(total_steps))


#used to get a range that includes both end points instead of the half-included and half-excluded
def inclusive_range(start:int,stop:int,step:int) -> range:
    return range(start,stop+step,step)


def main():
    parser = argparse.ArgumentParser(description="Find the % of AVW of most v2 polls")
    
    if GUI_mode:
        poll_id_label      = "Poll ID"
        rpc_username_label = "RPC Username"
        rpc_password_label = "RPC Password"
        rpc_port_label     = "RPC Port"
    else:
        poll_id_label      = "poll_id"
        rpc_username_label = "rpc_username"
        rpc_password_label = "rpc_password"
        rpc_port_label     = "-rpc_port"

    parser.add_argument("rpc_username", type=str, metavar=rpc_username_label, help="Your RPC username as it is in your config")
    parser.add_argument("rpc_password", type=str, metavar=rpc_password_label, help="Your RPC password as it is in your config")
    parser.add_argument("poll_id",      type=str, metavar=poll_id_label,      help="The ID of the poll. You can find this by using the listpolls RPC command or by using a blockchain explorer like Gridcoinstats.eu")
    parser.add_argument("-rpc_port",    type=int, metavar=rpc_port_label,     help="RPC port if set to be different from the default of 15715"   , default=15715, nargs="?")
    args = parser.parse_args()

    #give nicer names after parsing
    poll_id:str      = args.poll_id
    rpc_password:str = args.rpc_password
    rpc_username:str = args.rpc_username
    rpc_port:int     = args.rpc_port

    #attempt to open RPC connection
    rpc_caller = rpc.RPC(rpc_username, rpc_password, rpc_port)

    if rpc_caller.call("help") == None: #use help command to test connection
        sys.exit("Error: unable to connect to your wallet. Make sure your wallet is running and that your username and password are correct")

    #Get poll TX info
    #Note: a poll ID is just a TX ID
    txInfo = rpc_caller.call("gettransaction",params=poll_id, silent_error=True) #don't print the error message since we already talk about invalid IDs
    if txInfo == None:
        sys.exit("Error: Invalid poll ID")

    #check that its a v2 poll. Possible that a minor update in the future still works with the script, so show as warning
    if txInfo["contracts"][0]["body"]["version"] != 2:
        print("Warn: poll version is not v2. This may break this script")

    try:
        poll_title:str  = txInfo["contracts"][0]["body"]["title"]
    except KeyError:
        sys.exit("Error: Invalid poll ID") #means that they entered a random TX ID that wasn't a poll

    print("Looking at the poll with title: \"" + poll_title + "\"")
    print()

    #find out poll information
    #Note: all times are UNIX timestamps
    poll_start_block_hash:str  = txInfo["blockhash"]
    poll_start_time:int        = txInfo["time"]
    poll_length:int            = txInfo["contracts"][0]["body"]["duration_days"]
    poll_end_time:int          = poll_start_time + (24*60*60*poll_length)
    
    poll_start_block:int = rpc_caller.call("getblock",poll_start_block_hash)["height"]
    cur_time:int = rpc_caller.call("currenttime")["Unix"]
    cur_block:int = rpc_caller.call("getblockcount")
    
    #determine if the poll is running and get an end block
    poll_end_block:int
    if cur_time >= poll_end_time:
        #poll has ended
        print("Poll started at block " + str(poll_start_block) + " and has ended. Finding when it ended" + progress(step=1))
        
        # Run a binary search to find the block the poll ended
        # Look for the block with a timestamp right after the poll's expiration date
        checks = poll_start_block.bit_length()
        cur_check = 0

        for place in inclusive_range(start=checks+1, stop=0, step=-1): #add one to account to bit_length for the possibility of a rollover to the next bit
            bit = 2**place #(example: 0b10000000 or 0b01000000)
            cur_check += bit

            if cur_check > poll_start_block: #If cur_check is before the poll has started, the larger number is closer, so only check if it's after
                if cur_check > cur_block: #if cur_check is after the latest block, it cannot have a 1 in this bit
                    cur_check ^= bit  # flip the bit back to a 0
                    continue

                block_time = rpc_caller.call("getblockbynumber", cur_check)["time"]

                if block_time > poll_end_time and place != 0:#"and place != 0" allows a higher block if only one block away since we want the block immediately after the end and not before it
                    cur_check ^= bit

        poll_end_block = cur_check

        print("Poll ended at block " + str(poll_end_block))
        print()

    else:
        #poll is still running
        print("The poll is still running. Using the current block to compute AVW so far" + progress(step=1))
        print()
        poll_end_block =  cur_block #not technically an end but treat it as one

    #compute money supply
    print("Finding the average money supply" + progress(step=2))
    start_money_supply = rpc_caller.call("getblock", poll_start_block_hash)["MoneySupply"]
    end_money_supply   = rpc_caller.call("getblockbynumber", poll_end_block)["MoneySupply"]
    avg_money_supply   = (start_money_supply + end_money_supply)/2 
    #is technically an approximation since only end points are used 
    #computing the average by every blocks is extremely expensive and only causes negligible changes most of the time
    print("Average money supply is " + str(round(avg_money_supply))) 
    print()

    print("Finding the average pool magnitudes (this may take a minute)" + progress(step=3))
    #CPIDs of pools from the list hardcoded in the wallet
    pool_cpids=[
        "7d0d73fe026d66fd4ab8d5d8da32a611", #grcpool1_cpid
        "a914eba952be5dfcf73d926b508fd5fa", #grcpool2_cpid
        "163f049997e8a2dee054d69a7720bf05", #grcpool3_cpid
        "326bb50c0dd0ba9d46e15fae3484af35", #arikado_cpid
    ]

    avg_pool_magnitudes = 0
    for cpid in pool_cpids:
        data:dict = rpc_caller.call("superblocks",params=[cur_block - poll_start_block, False, cpid])
        
        magnitude_sum:int = 0
        superblock_count:int = 0
        for superblock in data:
            if int(superblock["height"]) < poll_end_block: #check that it's not after the poll has ended
                magnitude_sum += superblock["Magnitude"]
                superblock_count += 1

        #add to the total average magnitudes of the CPIDs
        avg_pool_magnitudes += magnitude_sum/superblock_count 
    
    print("Average magnitude is " + str(avg_pool_magnitudes))
    print()

    print("Finding average difficulty (this may take a minute)" + progress(step=4))
    block_range_data = rpc_caller.call("getblockstats",[0, poll_start_block, poll_end_block])
    avg_diff:int = block_range_data["averages"]["posdiff"]
    print("Average difficulty is " + str(avg_diff))
    print()

    print("Finding poll voteweight (this may take a minute)" + progress(step=5))
    voteweight = rpc_caller.call("getpollresults",poll_id)["total_weight"]
    print("voteweight is " + str(voteweight))
    print()

    total_network_magnitude=115_000
    avw = (avg_diff* 9544371.769) + ((total_network_magnitude - avg_pool_magnitudes)* (avg_money_supply/total_network_magnitude)/5.67)
    print("AVW is " + str(avw))
    print()
    
    print("----------")
    print("% of AVW is " + str(voteweight/avw * 100))

    print("----------")


if GUI_mode:
    #apply decorator (just without the @)
    main = Gooey(
        main,
        program_name="AVW Calculator",
        default_size=(610, 700), #slightly taller for longer output and showing optional arguments without scrolling
        
        progress_regex=r"step (?P<current>\d+)/(?P<total>\d+)$", #get current and total steps
        progress_expr="(current-1) / total * 100", #subtract 1 so it doesn't show as 100% at the last step
        
        menu=[
            {"name": "Help With RPC Setup",
             "items": [{"type": "MessageDialog",
                        "menuTitle": "How to Setup RPC",
                        "message": ("First, go to your config file (Settings-> open config file) and add the following lines:\n\n"
                                    + "server=1\n"
                                    + "rpcallowip=127.0.0.1\n"
                                    + "rpcuser=<USERNAME>\n"
                                    + "rpcpassword=<PASSWORD>\n\n"
                                    + "Make sure to replace the values in <>. Use that username and password as the RPC Username and RPC Password in this program."
                                    + "Now restart your wallet and when it boots up, you should be able to run this program now"
                                    )
                        }
                       ]
             },
            {"name": "About AVW",
             "items": [
                 {"type": "MessageDialog",
                  "menuTitle": "Brief Info About AVW",
                  "message": "AVW (active vote weight) is a measure of the amount of vote weight. All polls but option/casual polls much get a certain % of AVW for their results to count"
                  },
                 {"type": "Link",
                  "menuTitle": "Relevent Wiki Page",
                  "url": "https://gridcoin.us/wiki/voting.html"
                  }
             ]
             },
        ]
    )

main()
