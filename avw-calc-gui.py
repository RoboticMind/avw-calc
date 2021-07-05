from gooey import Gooey
from avwcalc import main


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

main(GUI_mode=True) #run the program

