#include <algorithm>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
// Owned event-delivery model,not a processor,firmware ISA or silicon simulator.
int main(int argc,char** argv) {
    try {
        if(argc!=3)throw std::runtime_error("Expected model cfg and command image");
        std::ifstream cfg(argv[1]),image(argv[2]);if(!cfg||!image)throw std::runtime_error("Missing original input");
        std::map<std::string,int> c;std::string key;int value;
        while(cfg>>key>>value)if(!c.emplace(key,value).second)throw std::runtime_error("Duplicate model property");
        if(!cfg.eof()||c.size()!=8)throw std::runtime_error("Invalid model cfg");
        for(auto k:{"actual_fuse","fuse_readable","feature","fast_mode","exception_enabled","power_on"})
            if(c.at(k)!=0&&c.at(k)!=1)throw std::runtime_error("Binary model property required");
        if(c.at("revision")<1||c.at("revision")>2||c.at("guard_need")<1||c.at("guard_need")>4)throw std::runtime_error("Model bound");
        std::cout<<"HEADER opentools.owned-erratum-model.v1\n";
        for(auto k:{"revision","feature","fast_mode","guard_need","exception_enabled","power_on"})std::cout<<"META "<<k<<" "<<c.at(k)<<"\n";
        std::cout<<"META fuse "<<(c.at("fuse_readable")?std::to_string(c.at("actual_fuse")):"X")<<"\n";
        int pending=0,visible=0,guard=0,active_ticks=0,ack=0,data=-1,check=0,seq=0;
        bool base=false,wa=false,force=false,wrote=false,issued=false,wa_phase=false;
        std::string line;
        while(std::getline(image,line)) {
            if(line.empty()||line[0]=='#')continue;
            std::istringstream s(line);std::string op,extra;int arg;
            if(!(s>>op>>arg)||s>>extra||issued)throw std::runtime_error("Invalid/late command");
            if(op=="WRITE"){if(wrote||arg!=42)throw std::runtime_error("One owned payload42");pending=arg;wrote=true;}
            else if(op=="BASE_FENCE"){if(!wrote||arg!=0||wa_phase)throw std::runtime_error("Invalid base fence");visible=pending;base=true;}
            else if(op=="WA_FENCE"){if(!wrote||arg!=0)throw std::runtime_error("Invalid WA fence");visible=pending;wa=true;wa_phase=true;}
            else if(op=="WA_GUARD"){if(!wrote||arg<1||arg>4)throw std::runtime_error("Invalid guard");guard=arg;force=true;wa_phase=true;}
            else if(op=="ISSUE") {
                if(!wrote||arg!=0)throw std::runtime_error("Invalid issue");
                issued=true;
                bool capture_bug=c.at("feature")&&c.at("fast_mode")&&c.at("revision")<2&&!c.at("actual_fuse");
                for(int tick=0;tick<std::max(guard,1);++tick) {
                    bool clock_active=force||tick==0;
                    if(clock_active)++active_ticks;
                    if(c.at("power_on")&&(!capture_bug||active_ticks>=c.at("guard_need")))ack=1;
                    std::cout<<"TICK "<<tick<<" "<<clock_active<<" "<<active_ticks<<" "<<ack<<" "<<visible<<"\n";
                }
                data=ack?((c.at("feature")&&c.at("fast_mode"))?visible:pending):-1;
                check=ack&&data==42;
            } else throw std::runtime_error("Unsupported command");
            std::cout<<"TRACE "<<++seq<<" "<<op<<" "<<arg<<" "<<visible<<" "<<pending
             <<" "<<base<<" "<<wa<<" "<<guard<<" "<<force<<" "<<active_ticks<<" "<<ack<<" "<<data<<" "<<check<<"\n";
        }
        if(!issued)throw std::runtime_error("No selected issue");
        std::cout<<"RESULT "<<ack<<" "<<data<<" "<<check<<" "<<(c.at("exception_enabled")&&force)<<" "<<active_ticks<<"\n";
        std::cout<<"OPENTOOLS_ERRATUM_RUN_COMPLETE\n";return 0;
    } catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
