"""Positive-centroid ridge adapter; missing tags are never converted into negative labels."""
import numpy as np
import review_pack as rp


def unit(x):
    x=np.asarray(x,dtype=np.float64)
    rp.require(x.ndim==2 and x.size and np.isfinite(x).all(),'Finite nonempty matrix required')
    norms=np.linalg.norm(x,axis=1,keepdims=True);rp.require(np.all(norms>1e-12),'Zero vector refused')
    return x/norms


def targets(prototypes, positives):
    p=unit(prototypes);result=[]
    for ids in positives:
        rp.require(ids and len(set(ids))==len(ids) and all(type(i)is int and 0<=i<len(p)for i in ids),'Observed positive tag indices required')
        result.append(p[ids].mean(axis=0))
    return unit(result)


def objective(x,y,w,regularization):
    return float(np.sum((x@w-y)**2)+regularization*np.sum((w-np.eye(w.shape[0]))**2))


def fit(x,y,regularization):
    x=np.asarray(x,dtype=np.float64);y=np.asarray(y,dtype=np.float64)
    rp.require(x.ndim==y.ndim==2 and x.shape==y.shape and x.size and np.isfinite(x).all()and np.isfinite(y).all(),'Matching finite audio/target matrices required')
    rp.require(type(regularization)in(int,float)and np.isfinite(regularization)and regularization>0,'Positive fixed regularization required')
    eye=np.eye(x.shape[1]);w=eye+x.T@np.linalg.solve(x@x.T+regularization*np.eye(len(x)),y-x)
    before=objective(x,y,eye,regularization);after=objective(x,y,w,regularization)
    gradient=x.T@(x@w-y)+regularization*(w-eye)
    rp.require(np.isfinite(w).all()and after<=before+1e-10 and np.max(np.abs(gradient))<1e-7,'Ridge optimum verification failed')
    return w,{'objective_before':before,'objective_after':after,'MSE_before':float(np.mean((x-y)**2)),
              'MSE_after':float(np.mean((x@w-y)**2)),'normal_equation_max_abs_residual':float(np.max(np.abs(gradient))),
              'parameter_delta_frobenius_norm':float(np.linalg.norm(w-eye)),'fit_tracks':len(x),
              'parameter_count':int(w.size),'regularization':regularization,'generalization_evaluated':False}


def observed_recall(x,prototypes,positives,k=5):
    scores=unit(x)@unit(prototypes).T;values=[]
    for row,ids in zip(scores,positives):
        rp.require(ids and all(type(i)is int and 0<=i<len(row)for i in ids),'Known positive indices required')
        top=sorted(range(len(row)),key=lambda i:(-float(row[i]),i))[:k]
        values.append(len(set(top)&set(ids))/len(set(ids)))
    rp.require(len(values)==len(x),'Positive label rows missing')
    return {'macro_observed_tag_recall_at5':float(np.mean(values)),'tracks':len(values),
            'scope':'training_diagnostic_only_not_precision_or_full_relevance_or_test_accuracy'}
