#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
// Owned sampled device emulator. Saved receipts live in the host,not silicon RAM.
struct Device {
    unsigned status=0,epoch=0,saved=0,saved_epoch=0,rd=0,rd_epoch=0;
    bool saved_valid=false,rd_valid=false,accepted=false,error=false;
    bool warm_clears,read_clears,power;
    Device(bool warm,bool destructive,bool on):warm_clears(warm),read_clears(destructive),power(on){}
    void reset(bool por) {
        rd_valid=false;rd=0;rd_epoch=0;
        if(por||warm_clears){status=0;++epoch;}
    }
    void step(const std::string& op) {
        accepted=false;error=false;
        if(op=="POR")reset(true);
        else if(op=="WARM")reset(false);
        else if(op=="FAULT")status|=1;
        else if(op=="READ"||op=="MONITOR") {
            rd_valid=false;
            if(power){rd=status;rd_epoch=epoch;rd_valid=true;accepted=true;if(read_clears){status=0;++epoch;}}
            else error=true;
        } else if(op=="SAVE") {
            if(rd_valid){saved=rd;saved_epoch=rd_epoch;saved_valid=true;accepted=true;}
        } else if(op=="RECORD") {
            rd_valid=false;
            if(power){rd=saved;rd_epoch=saved_epoch;rd_valid=saved_valid;accepted=saved_valid;}
            else error=true;
        } else if(op!="INIT")throw std::runtime_error("Unknown operation");
    }
    void emit(int tick,int period,const std::string& op)const {
        std::cout<<"ROW "<<tick<<" "<<1000+period*tick<<" "<<op<<" "<<status<<" "<<epoch
        <<" "<<saved<<" "<<saved_epoch<<" "<<saved_valid<<" "<<rd<<" "<<rd_epoch
        <<" "<<rd_valid<<" "<<accepted<<" "<<error<<" "<<power<<"\n";
    }
};
int main(int argc,char** argv) {
    try {
        if(argc!=3)throw std::runtime_error("Expected device cfg and command image");
        std::ifstream cfg(argv[1]),image(argv[2]);if(!cfg||!image)throw std::runtime_error("Missing original input");
        std::map<std::string,std::string> values;std::string key,value;
        while(cfg>>key>>value)if(!values.emplace(key,value).second)throw std::runtime_error("Duplicate device property");
        if(!cfg.eof()||values.size()!=7)throw std::runtime_error("Invalid device cfg");
        int period=std::stoi(values.at("clock_ns"));
        if(period<1||period>1000000)throw std::runtime_error("Clock outside owned model");
        for(auto k:{"read_clears","warm_clears","board_power"})if(values.at(k)!="0"&&values.at(k)!="1")throw std::runtime_error("Binary property required");
        std::stoi(values.at("fuse"));values.at("revision");values.at("clock_id");
        Device d(values.at("warm_clears")=="1",values.at("read_clears")=="1",values.at("board_power")=="1");
        std::cout<<"HEADER opentools.owned-bringup-emulation.v1\n";
        for(const auto& entry:values)std::cout<<"META "<<entry.first<<" "<<entry.second<<"\n";
        std::cout<<"ANCHOR 0 1000\nANCHOR 8 "<<1000+8*period<<"\n";
        d.emit(0,period,"INIT");int last=0;std::string line;
        while(std::getline(image,line)) {
            if(line.empty()||line[0]=='#')continue;
            std::istringstream s(line);int tick;std::string op,extra;
            if(!(s>>tick>>op)||s>>extra||tick<=last||tick>8)throw std::runtime_error("Monotonic bounded image required");
            if(last==0&&op!="POR"&&op!="WARM")throw std::runtime_error("Explicit entry reset required");
            last=tick;d.step(op);d.emit(tick,period,op);
        }
        if(last==0)throw std::runtime_error("Empty image");
        std::cout<<"OPENTOOLS_BRINGUP_RUN_COMPLETE\n";return 0;
    } catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
