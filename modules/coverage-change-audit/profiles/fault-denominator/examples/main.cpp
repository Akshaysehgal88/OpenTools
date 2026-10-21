#include "Vtop.h"
#include "verilated.h"
#include "plans.hpp"
#include <iostream>
#include <vector>
#include <string>
#include <map>
int main(int argc,char**argv){
 if(argc!=2)return 3;unsigned selection=0;for(const char*q=argv[1];*q;++q){if(*q<'0'||*q>'9')return 3;selection=selection*10+(*q-'0');}
 if(selection>=sizeof(PLANS)/sizeof(PLANS[0]))return 3;
 const Plan&p=PLANS[selection];VerilatedContext context;Vtop d{&context};unsigned checks=0,failures=0;
 auto check=[&](bool okay){++checks;failures+=!okay;};
 std::cout<<"FAULT_CAMPAIGN 1\nCONFIG "<<selection<<' '<<N<<' '<<S<<' '<<O<<' '<<p.mode<<' '<<p.legal_mask<<' '<<p.legal_value<<' '<<p.patterns<<' '<<p.budget<<' '<<p.excluded<<' '<<p.unknown_fault<<' '<<p.metric<<' '<<p.basis<<'\n';
 std::vector<unsigned> legal,gold,chosen;std::vector<std::vector<unsigned>> outputs(2*S);std::vector<unsigned> representatives(2*S);std::vector<std::string> classes(2*S);
 for(unsigned v=0;v<(1u<<N);++v)if((v&p.legal_mask)==p.legal_value){
  legal.push_back(v);if(p.patterns&(1u<<v))chosen.push_back(v);
  d.P_STIMULUS=v;d.P_TEST_MODE=p.mode;d.P_FAULT_ENABLE=0;d.P_FAULT_SITE=0;d.P_STUCK_VALUE=0;d.eval();
  check(d.P_STIMULUS==v&&d.P_TEST_MODE==p.mode&&!d.P_FAULT_ENABLE);
  gold.push_back(d.P_OBSERVED);std::cout<<"GOLD "<<unsigned(d.P_STIMULUS)<<' '<<unsigned(d.P_TEST_MODE)<<' '<<unsigned(d.P_RAW_SITES)<<' '<<unsigned(d.P_DRIVEN_SITES)<<' '<<unsigned(d.P_OBSERVED)<<'\n';
 }
 if(legal.empty()||chosen.empty())return 3;
 for(unsigned f=0;f<2*S;++f){
  for(unsigned i=0;i<legal.size();++i){
   unsigned v=legal[i];d.P_STIMULUS=v;d.P_TEST_MODE=p.mode;d.P_FAULT_ENABLE=1;d.P_FAULT_SITE=f/2;d.P_STUCK_VALUE=f%2;d.eval();
   check(d.P_STIMULUS==v&&d.P_TEST_MODE==p.mode&&d.P_FAULT_ENABLE&&d.P_FAULT_SITE==f/2&&d.P_STUCK_VALUE==f%2);
   outputs[f].push_back(d.P_OBSERVED);
   std::cout<<"ORACLE "<<f<<' '<<unsigned(d.P_FAULT_SITE)<<' '<<unsigned(d.P_STUCK_VALUE)<<' '<<unsigned(d.P_STIMULUS)<<' '<<unsigned(d.P_TEST_MODE)<<' '<<unsigned(d.P_RAW_SITES)<<' '<<unsigned(d.P_DRIVEN_SITES)<<' '<<unsigned(d.P_OBSERVED)<<' '<<gold[i]<<'\n';
  }
  unsigned representative=f;for(unsigned old=0;old<f;++old)if(outputs[f]==outputs[old]){representative=representatives[old];break;}representatives[f]=representative;
  int witness=-1;unsigned sampled=0;for(unsigned v:chosen){if(sampled>=p.budget)break;++sampled;unsigned i=0;while(legal[i]!=v)++i;if(outputs[f][i]!=gold[i]&&witness<0)witness=v;}
  bool detectable=outputs[f]!=gold;std::string classification=witness>=0?"DT":sampled<chosen.size()?"AB":!detectable?"UT":"UD";if(int(f)==p.unknown_fault)classification="UNKNOWN";classes[f]=classification;
  std::cout<<"FAULT "<<f<<' '<<classification<<' '<<sampled<<' '<<witness<<' '<<detectable<<' '<<representative<<' '<<bool(p.excluded&(1u<<f))<<'\n';
 }
 unsigned original_num=0,original_den=0,collapsed_num=0,collapsed_den=0,groups=0;
 for(unsigned f=0;f<2*S;++f){
  if(!(p.excluded&(1u<<f))){original_num+=classes[f]=="DT";original_den+=p.metric==0||classes[f]!="UT";}
  if(representatives[f]!=f)continue;++groups;unsigned members=0,included=0;bool detected=false,all_ut=true;
  for(unsigned member=0;member<2*S;++member)if(representatives[member]==f){++members;if(!(p.excluded&(1u<<member))){++included;detected|=classes[member]=="DT";all_ut&=classes[member]=="UT";}}
  if(included){collapsed_num+=detected;collapsed_den+=p.metric==0||!all_ut;}
  std::cout<<"GROUP "<<f<<' '<<members<<' '<<included<<' '<<detected<<' '<<all_ut<<'\n';
 }
 std::cout<<"RESULT "<<2*S<<' '<<groups<<' '<<original_num<<' '<<original_den<<' '<<collapsed_num<<' '<<collapsed_den<<' '<<(p.basis?collapsed_num:original_num)<<' '<<(p.basis?collapsed_den:original_den)<<"\nNATIVE_CHECKS "<<checks<<' '<<failures<<'\n';
 d.final();return failures?1:0;
}
