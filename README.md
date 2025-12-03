## KEDA demo
https://github.com/kedacore/http-add-on

### Requirements
- docker - https://www.docker.com/
- kind - https://kind.sigs.k8s.io/
- kubectl - https://kubernetes.io/docs/tasks/tools/
- helm - https://helm.sh/
- k9s - https://k9scli.io/
- hey - https://github.com/rakyll/hey

### Build container

```
docker build --progress plain -t local/app:v0.1.0 -f Dockerfile .
```

### Create kind cluster
```
kind create cluster --config=k8s/kind/config.yaml
```

### Install nginx
```
kubectl config use-context kind-keda-demo
kubectl apply -f k8s/kind/ingress-nginx.yaml
```
The configuration (nginx and kind) above maps ingress ports 80 and 443 to host ports 8000 and 8443, respectively.  

### Upload built image to the kind cluster
```
kind load docker-image local/app:v0.1.0 --name keda-demo
```
Tip: the following command helps to list images available inside of the kind cluster:  
`docker exec -it keda-demo-control-plane crictl images`

### Deploy application without KEDA
```
kubectl apply -f k8s/manifests/deployment
kubectl apply -f k8s/manifests/service
```
Check whether the application is running and accessible on the host at http://localhost:8000/

#### Application load testing using request generation
Without overloading
```
hey -c 10 -q 1 -z 30s http://localhost:8000/
```

With overloading
```
hey -c 45 -q 1 -z 30s http://localhost:8000/
```

#### Remove application ingress and service
```
kubectl delete -f k8s/manifests/service
```

### Install KEDA
Add Helm repository
```
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
```

Install KEDA version 2.17.2
```
helm upgrade --install keda kedacore/keda --version 2.17.2 \
  --namespace keda --create-namespace --wait
```

Install KEDA HTTP Add-on version 0.11.0
```
helm upgrade --install keda-http-addon kedacore/keda-add-ons-http  \
  --values k8s/helm-values/keda-http-addon.yaml --version 0.11.0 \
  --namespace keda --wait
```

### Deploy application ingress and service with KEDA configuration
```
kubectl apply -f k8s/manifests/service-with-keda
```

### Test KEDA Autoscaling with request generation
```
hey -c 45 -q 1 -z 60s http://localhost:8000/
```
Once the request generation is stopped, KEDA will detect idleness and scale the application back to zero replicas in about two minutes.
