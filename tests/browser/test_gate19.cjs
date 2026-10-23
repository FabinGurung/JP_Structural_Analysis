const test=require("node:test"),a=require("node:assert/strict");
const {triage}=require("../../site/gate19.js");
const src='$ CONTROLS\n UNITS "N" "MM" "C"\n$ STORIES - IN SEQUENCE FROM TOP\n STORY "Story3"\n STORY "Story2"\n STORY "Story1"\n STORY "Base"\n$ POINT COORDINATES\n POINT "1" 0 0\n$ LINE CONNECTIVITIES\n LINE "B1" BEAM "1" "1"\n$ AREA CONNECTIVITIES\n AREA "A1" FLOOR 3 "1" "2" "3"\n$ LINE ASSIGNS\n LINEASSIGN "B1" "Story1" SECTION "B"\n$ AREA ASSIGNS\n AREAASSIGN "A1" "Story1" SECTION "S"\n$ MASS SOURCE\n MASSSOURCE "Ms1" INCLUDELOADS "Yes"\n$ END OF MODEL FILE';
test("local syntactic candidate never becomes engineering approval",()=>{
 const x=triage(src,"candidate.e2k");
 a.equal(x.status,"LOCAL_SHAPE_CANDIDATE_IDENTITY_HOLD");
 a.equal(x.sourceIdentityVerified,false);a.equal(x.engineeringApproval,false);
});
test("foreign project, missing footer, wrong units rejected",()=>{
 a.equal(triage(src,"Narayani.e2k").status,"REJECT");
 a.equal(triage(src.replace("$ END OF MODEL FILE",""),"candidate.e2k").status,"REJECT");
 a.equal(triage(src.replace('"N" "MM"','"KN" "M"'),"candidate.e2k").status,"REJECT");
});
