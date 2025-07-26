"""
Comprehensive error logging and analytics system for the Instagram auto signup system.
"""

import json
import hashlib
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from collections import defaultdict, deque
from enum import Enum
import traceback
import threading

from .logging_config import get_logger
from .statistics_manager import get_statistics_manager


logger = get_logger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    NETWORK = "network"
    SELENIUM = "selenium"
    EMAIL_SERVICE = "email_service"
    PROXY = "proxy"
    INSTAGRAM = "instagram"
    VALIDATION = "validation"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for an error."""
    component: str
    operation: str
    user_agent: Optional[str] = None
    proxy_ip: Optional[str] = None
    email_service: Optional[str] = None
    account_data: Optional[Dict[str, Any]] = None
    browser_info: Optional[Dict[str, Any]] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorRecord:
    """Detailed error record."""
    error_id: str
    timestamp: datetime
    error_type: str
    error_message: str
    category: ErrorCategory
    severity: ErrorSeverity
    context: ErrorContext
    stack_trace: Optional[str] = None
    resolution_attempted: List[str] = field(default_factory=list)
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        if self.resolution_time:
            result['resolution_time'] = self.resolution_time.isoformat()
        result['category'] = self.category.value
        result['severity'] = self.severity.value
        return result


@dataclass
class ErrorPattern:
    """Pattern of recurring errors."""
    pattern_id: str
    error_signature: str
    occurrences: int
    first_seen: datetime
    last_seen: datetime
    affected_components: Set[str]
    common_context: Dict[str, Any]
    suggested_fixes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result['first_seen'] = self.first_seen.isoformat()
        result['last_seen'] = self.last_seen.isoformat()
        result['affected_components'] = list(self.affected_components)
        return result

class 
ErrorAnalyzer:
    """Analyzes errors to identify patterns and suggest solutions."""
    
    def __init__(self):
        self.error_patterns: Dict[str, ErrorPattern] = {}
        self.resolution_strategies: Dict[str, List[str]] = {
            "selenium_element_not_found": [
                "Try alternative selectors",
                "Wait for element to load",
                "Refresh page and retry",
                "Check if Instagram UI changed"
            ],
            "network_timeout": [
                "Switch to different proxy",
                "Increase timeout duration",
                "Check network connectivity",
                "Retry with exponential backoff"
            ],
            "email_service_unavailable": [
                "Switch to backup email service",
                "Check service status",
                "Increase retry attempts",
                "Use different email domain"
            ],
            "instagram_rate_limit": [
                "Increase delay between requests",
                "Switch proxy/IP address",
                "Change user agent",
                "Wait for rate limit reset"
            ],
            "proxy_connection_failed": [
                "Remove proxy from pool",
                "Test proxy connectivity",
                "Switch to different proxy type",
                "Update proxy credentials"
            ]
        }
    
    def analyze_error(self, error_record: ErrorRecord) -> Dict[str, Any]:
        """Analyze an error and return insights."""
        # Generate error signature
        signature = self._generate_error_signature(error_record)
        
        # Update or create pattern
        pattern = self._update_error_pattern(error_record, signature)
        
        # Get suggested resolutions
        suggestions = self._get_resolution_suggestions(error_record, pattern)
        
        return {
            'error_signature': signature,
            'pattern_id': pattern.pattern_id if pattern else None,
            'occurrence_count': pattern.occurrences if pattern else 1,
            'suggested_resolutions': suggestions,
            'severity_assessment': self._assess_severity(error_record, pattern),
            'impact_analysis': self._analyze_impact(error_record, pattern)
        }
    
    def _generate_error_signature(self, error_record: ErrorRecord) -> str:
        """Generate a unique signature for the error type."""
        signature_data = {
            'error_type': error_record.error_type,
            'category': error_record.category.value,
            'component': error_record.context.component,
            'operation': error_record.context.operation
        }
        
        # Add specific context based on category
        if error_record.category == ErrorCategory.SELENIUM:
            if 'element_selector' in error_record.context.additional_data:
                signature_data['selector'] = error_record.context.additional_data['element_selector']
        elif error_record.category == ErrorCategory.NETWORK:
            if error_record.context.proxy_ip:
                signature_data['proxy_type'] = 'proxy'
        elif error_record.category == ErrorCategory.EMAIL_SERVICE:
            if error_record.context.email_service:
                signature_data['service'] = error_record.context.email_service
        
        # Generate hash
        signature_str = json.dumps(signature_data, sort_keys=True)
        return hashlib.md5(signature_str.encode()).hexdigest()[:12]
    
    def _update_error_pattern(self, error_record: ErrorRecord, signature: str) -> Optional[ErrorPattern]:
        """Update or create error pattern."""  ]       >= cutoff
ast_seenif pattern.l     ()
       ns.valuespatter self.error_n in pattertern forpat          urn [
        ret)
  ours=hours(hmedelta.now() - ti datetimetoff =      cu"
   hours.""ent rectterns fromrror pa"Get e   ""]:
     rrorPatternt[E> Lis int = 24) -ours:(self, hent_patternset_recf g  de
    
  limit]    )[:    rue
=T     reverse
       s,occurrencembda p: p.=la        key),
    es(rns.valute.error_pat     self
       n sorted(tur     re"""
   urrence. by occterns error pat""Get top   "   n]:
  rorPatter) -> List[Erit: int = 10lf, limrns(set_top_patte    def ge    
pact
rn im     retu
         
  e'ratde 'moend'] =trimpact['                 e:
         els        table'
  nd'] = 'sre't     impact[          :
     ate < 1elif r               sing'
  'increatrend'] =impact['               
      rate > 5:          if   our
   ors per h# err3600)  ime_diff / rrences / (tcu pattern.oc rate =            :
   > 0 time_diff           if  seconds()
.total_rst_seen)- pattern.fi.last_seen attern = (pme_diffti     
       ndermine tre Det  #             
  
       rrencesern.occucy'] = pattequen'fr impact[         ts)
  ted_componenattern.affect(pts'] = lisonented_compfecimpact['af           ttern:
     if pa 
    }
              'new'
  trend':      '  ': 1,
    uency     'freq],
       .componentd.context[error_recorts': mponend_co 'affecte           ion],
ratopeext.ecord.contor_rs': [erroperationed_   'affect         
ct = {mpa     i"""
   of an error.e impact alyze th """An  
     ny]:r, A-> Dict[storPattern]) rrional[Ern: OptpatterRecord, rror_record: Ef, erroselact(analyze_imp def _
   ity
     severurn   ret       
   ITICAL
   rity.CRSeve = Error    severity            s > 50:
rencecurtern.oc   elif pat         
HIGHrity.rSeve Erroy =verit         se
           ty.MEDIUM:ErrorSeveririty == ve     elif se          ty.MEDIUM
 rSeveri Erro  severity =          
        y.LOW:veritrSety == Erroseverif  i         :
      rences > 10ttern.occur pa     if:
        pattern   ifcy
     quentern freatbased on pse severity crea  # In        
      
verityor_record.se errerity =
        sev""" error. anerity ofhe sev t""Assess
        "everity:ErrorS> rPattern]) -l[Erro: Optiona patternecord, ErrorRcord:re, error_elf_severity(ssess _as   
    defcates
 move dupliReons))  # tiugges(sst(set   return li
             xes)
d_fi.suggestend(patternextetions.   sugges
         ted_fixes:es.suggnd patterntern a   if patons
     fic suggestipecitern-s Add pat      #        
  )
error_key]egies[lution_stratself.resotend(ggestions.ex  su         :
 esgion_strate.resolutikey in self   if error_"
     ' ', '_')}).replace(.lower(_typeerrorrd.eco_{error_rvalue}ory.d.categor_recror f"{er error_key =      or type
 erron based stions et sugge     # G   
   
     ions = []est       sugg"""
 ror.er an estions forion sugg"Get resolut "":
       tr]]) -> List[stternonal[ErrorPan: Opti patterrrorRecord,ecord: Eor_rs(self, errstiontion_suggeget_resolu    def _ext
    
cont return        
        
agentr_used.context.coror_re = erragent']'user_ext[ cont         _agent:
  t.userntexr_record.co   if erroice
     rvl_setext.emai.conor_record'] = errservice['email_ontext c     
      _service:ontext.emaild.cror_recor       if erproxy_ip
 ntext..corror_record] = e_ip'text['proxy    con
        xy_ip:ontext.prorecord.cerror_
        if         {}
  context = ""
      or record." from errn contextmo com""Extract "]:
       tr, Any> Dict[sord) -rorReccord: Erlf, error_re(sext_contect_commonef _extra  
    dpattern
  n retur         
  ttern
     pature] = rns[signate.error_pat        self)
             ord)
   ror_recn_context(ert_commoxtracxt=self._eteommon_con  c             ,
 mponent}ontext.cord.c_reco={errortsenmponected_co         aff      
 ,tampd.timesoren=error_recast_se   l         stamp,
    rd.timer_recoeen=erro_s    first           rences=1,
 urocc         ,
       ignaturee=surator_signerr             ",
   e}signatur_{rnatten_id=f"p      patter         
 n(orPatterrn = Err  patte       
   new pattern   # Create      e:
    ls
        emponent)text.corecord.conor_dd(errmponents.aected_copattern.aff            tamp
record.timesen = error_setern.last_    pat     
   s += 1ncen.occurreter         pate]
   gnaturatterns[si.error_ptern = self        pat    ng pattern
e existiUpdat   # 
         or_patterns:in self.errture    if signa
     