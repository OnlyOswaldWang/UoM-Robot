#!/usr/bin/env python3
"""Render a readable English iCalendar while preserving original event identities and timing."""
import os,re,datetime
from urllib.request import Request,urlopen
from zoneinfo import ZoneInfo
from pathlib import Path

def unfold(s):
    out=[]
    for line in s.replace("\r\n","\n").replace("\r","\n").split("\n"):
        if line.startswith((" ","\t")) and out: out[-1]+=line[1:]
        else: out.append(line)
    return out

def unesc(s):
    return re.sub(r'\\([nN\\;,])',lambda m:"\n" if m[1].lower()=="n" else m[1],s)
def esc(s):
    return str(s).replace("\\","\\\\").replace("\n","\\n").replace(";","\\;").replace(",","\\,")
def fold(s):
    parts=[]; chunk=""; n=0
    for c in s:
        b=len(c.encode())
        if n+b>75:
            parts.append(chunk);chunk=" "+c;n=b+1
        else: chunk+=c;n+=b
    parts.append(chunk)
    return "\r\n".join(parts)
def name(s): return s.split(":",1)[0].split(";",1)[0].upper()
def value(s): return s.split(":",1)[1] if ":" in s else ""
def field(d,k):
    m=re.search(r'(?:^|\n)'+re.escape(k)+r':\s*(.*?)(?=\n|$)',d,re.I)
    return m[1].strip() if m else ""
def staff(s):
    p=[x.strip() for x in s.split(",") if x.strip()]
    return "; ".join(p[i+1]+" "+p[i] for i in range(0,len(p),2)) if p and len(p)%2==0 else (s or "Not provided")
def location(s):
    a=[]
    for p in s.split(", "):
        if "_" not in p:a.append(p);continue
        b,r=p.split("_",1)
        if b in ("Kilburn","Simon","Schuster","Nancy Rothwell"): b+=" Building"
        a.append(b+" · "+r.replace("RUTHERFORD TH","Rutherford Theatre").replace("TH ","Theatre "))
    return "; ".join(a)
def clock(lines,key):
    t=next((value(x) for x in lines if name(x)==key),"")
    try:
        if t.endswith("Z"): return datetime.datetime.strptime(t,"%Y%m%dT%H%M%SZ").replace(tzinfo=datetime.timezone.utc).astimezone(ZoneInfo("Europe/London")).strftime("%H:%M")
        return datetime.datetime.strptime(t,"%Y%m%dT%H%M%S").strftime("%H:%M")
    except ValueError: return "See event"
def transform_event(lines):
    props={name(x):value(x) for x in lines if ":" in x and not x.startswith(("BEGIN:","END:"))}
    desc=unesc(props.get("DESCRIPTION","")); original=unesc(props.get("SUMMARY",""))
    typ=field(desc,"Event type").upper() or "UNSPECIFIED"
    tags={"LECTURE":"LECTURE","LABORATORY":"LAB","DROP-IN":"DROP-IN","ONLINE TUTORIAL":"ONLINE","ASYNCHRONOUS":"ASYNC","COMPUTER CLASS":"COMPUTER","ACADEMIC ADVISEMENT":"ADVICE","PRESENTATIONS":"PRESENTATION"}
    tag=tags.get(typ,typ)
    codes=list(dict.fromkeys(re.findall(r'\b[A-Z]{3,5}\d{5}\b',field(desc,"Unit Code"))))
    course=field(desc,"Description").lstrip("_")
    chunks=[x.strip() for x in original.split("/") if x.strip()]
    specifics=[x for x in chunks[2:] if len(x)>3 and not re.fullmatch(r'SEM\d+|[0-9]+|<.*>',x,re.I)]
    if course in ("MSc Virtual Common Room","PGT Robotics Welcome Week") and specifics:course=specifics[0]
    if not course:course=" / ".join(codes) if codes else (specifics[0] if specifics else "University Session")
    label=f"[{tag}] {course}"
    if codes and course!=" / ".join(codes): label+=" | "+" / ".join(codes)
    loc=location(unesc(props.get("LOCATION","")) or field(desc,"Location"))
    note=field(desc,"Notes")
    if "ONLINE" in typ:mode="Online"
    elif typ=="ASYNCHRONOUS":mode="Asynchronous / Self-paced"
    elif loc:mode="In Person (inferred from location)"
    elif re.search(r'online|canvas|virtual',note,re.I):mode="Online (inferred from notes)"
    else:mode="Not specified"
    detail=[
        "Course: "+course,"Start Time: "+clock(lines,"DTSTART")+" (Europe/London)",
        "End Time: "+clock(lines,"DTEND")+" (Europe/London)",
        "Location: "+(loc or "Not provided"),"Event Type: "+typ.title(),
        "Host / Instructor: "+staff(field(desc,"Staff Member")),"Delivery Mode: "+mode,
        "","Other Information:","Unit Code: "+(", ".join(codes) if codes else "Not provided"),
        "Teaching Weeks: "+(field(desc,"Weeks") or "Not provided"),
        "Directions: "+(field(desc,"Directions") or "Not provided"),
        "Notes: "+(note or "Not provided"),
        "Map: "+(field(desc,"Map link") or "Not provided"),
        "Original University Title: "+original]
    new=[];depth=0
    for x in lines:
        if x.startswith("BEGIN:") and x!="BEGIN:VEVENT":depth+=1
        elif x.startswith("END:") and x!="END:VEVENT":depth-=1
        if depth==0 and name(x) in ("SUMMARY","DESCRIPTION","LOCATION"):continue
        if x=="END:VEVENT":
            new += ["SUMMARY:"+esc(label),"DESCRIPTION:"+esc("\n".join(detail))]
            if loc:new.append("LOCATION:"+esc(loc))
        new.append(x)
    return new

def format_ics(raw):
    lines=unfold(raw)
    if "BEGIN:VCALENDAR" not in lines or "END:VCALENDAR" not in lines:raise ValueError("Invalid ICS: calendar markers missing")
    output=[];evt=[];in_evt=False;count=0
    for line in lines:
        if line=="BEGIN:VEVENT":in_evt=True;evt=[line];continue
        if in_evt:
            evt.append(line)
            if line=="END:VEVENT":
                output+=transform_event(evt);in_evt=False;count+=1
            continue
        if line.startswith(("X-WR-CALNAME:","X-WR-CALDESC:")):continue
        if line=="END:VCALENDAR":
            # Merge locally maintained events every time the official calendar is refreshed.
            manual_path = Path(__file__).with_name("personal_events.json")
            if manual_path.exists():
                import json
                for event in json.loads(manual_path.read_text(encoding="utf-8")):
                    uid = event["uid"]
                    if not re.fullmatch(r"[A-Za-z0-9._@-]+", uid):
                        raise ValueError("Invalid manual event UID")
                    start_utc, end_utc = event["start_utc"], event["end_utc"]
                    if not (re.fullmatch(r"\\d{8}T\\d{6}Z", start_utc) and
                            re.fullmatch(r"\\d{8}T\\d{6}Z", end_utc)):
                        raise ValueError("Invalid manual event time")
                    output.extend([
                        "BEGIN:VEVENT",
                        "UID:" + uid,
                        "DTSTAMP:" + event["dtstamp"],
                        "DTSTART:" + start_utc,
                        "DTEND:" + end_utc,
                        "SUMMARY:" + esc(event["title"]),
                        "LOCATION:" + esc(event["location"]),
                        "DESCRIPTION:" + esc("\\n".join(event["description"])),
                        "STATUS:CONFIRMED",
                        "URL:" + event["url"],
                        "END:VEVENT",
                    ])
            output+=["X-WR-CALNAME:UoM | Robotics Timetable","X-WR-CALDESC:English University of Manchester timetable","REFRESH-INTERVAL;VALUE=DURATION:PT1H"]
        output.append(line)
    if in_evt or count==0:raise ValueError("No complete events found")
    return "\r\n".join(fold(x) for x in output)+"\r\n",count

if __name__=="__main__":
    url=os.environ["UPSTREAM_ICS_URL"]
    if not url.startswith("https://scientia-eu-v4-3-api-d3-02.azurewebsites.net/"):raise SystemExit("Unrecognized upstream host")
    r=urlopen(Request(url,headers={"User-Agent":"UoM-Timetable-Calendar/1.0"}),timeout=35)
    raw=r.read(10*1024*1024+1)
    if len(raw)>10*1024*1024:raise SystemExit("Source exceeds size limit")
    result,count=format_ics(raw.decode("utf-8-sig"))
    dest=Path("site/timetable.ics");dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(result.encode("utf-8"))
    print("Formatted",count,"events")
